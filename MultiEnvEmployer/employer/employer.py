import sys
import subprocess
import uuid
import pickle
import atexit
import weakref
from typing import Union, List, Optional, TYPE_CHECKING
from pathlib import Path

from MultiEnvEmployer.employer.YieldIterator import YieldIterator
from MultiEnvEmployer.employer.UReturnIterator import UReturnIterator
from MultiEnvEmployer.employer.OutputHandler import output_handler
from MultiEnvEmployer.employer.MessageReader import MessageReader
from MultiEnvEmployer.employer.Watchdog import Watchdog
from MultiEnvEmployer.utils.FileCache import FileCache
from MultiEnvEmployer.utils.errors import (
    TypeMessageNotFound,
    RemoteExecutionError,
    FailedIntrospectModule
)

if TYPE_CHECKING:
    from MultiEnvEmployer.remote.remote_module import RemoteModule


# Глобальный реестр для atexit
_employer_instances = weakref.WeakSet()


def _cleanup_all():
    """Очистка всех Employer при выходе из программы"""
    for emp in list(_employer_instances):
        try:
            emp.close()
        except Exception:
            pass


atexit.register(_cleanup_all)


class Employer:
    def __init__(
            self,
            project_dir: Path,
            venv_path: Path,
            cache_path: Path = None,
            pickle_protocol: int = 4,
            stream_threshold: int = 1024 * 1024,  # 1 MB
            chunk_size: int = 1024 * 1024  # 1 MB
    ):
        self.project_dir = Path(project_dir)
        venv_path = Path(venv_path)

        # Валидация pickle protocol
        if not isinstance(pickle_protocol, int) or pickle_protocol < 0 or pickle_protocol > pickle.HIGHEST_PROTOCOL:
            raise ValueError(
                f"Invalid pickle_protocol: {pickle_protocol}. "
                f"Must be between 0 and {pickle.HIGHEST_PROTOCOL}"
            )

        # Валидация пути к Python
        python_name = "python.exe" if sys.platform == "win32" else "python"
        self.python = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / python_name
        
        if not self.python.exists():
            # Попробуем без расширения
            self.python = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "python"
            if not self.python.exists():
                raise FileNotFoundError(f"Python interpreter not found in venv: {venv_path}")

        base_dir = Path(__file__).resolve().parent.parent

        self.worker_script = base_dir / "worker" / "worker.py"
        self.introspect_script = base_dir / "worker" / "introspection.py"

        self.pickle_protocol = pickle_protocol
        self.stream_threshold = stream_threshold
        self.chunk_size = chunk_size
        self._active_workers = {}
        self._dead_workers = []

        self.cache = FileCache(
            app_name="MultiEnvEmployer",
            version=None,
            cache_path=cache_path,
            max_items=50,
            pickle_protocol=pickle_protocol
        )

        # Регистрируем в глобальном реестре
        _employer_instances.add(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def cache_clear(self):
        """Функция очистки кэша"""
        self.cache.clear()

    def _cleanup_dead_workers(self):
        """Очистка списка мёртвых воркеров"""
        if len(self._dead_workers) > 100:
            self._dead_workers = self._dead_workers[-50:]

    def _cleanup_dead_processes(self):
        """Удаление мёртвых процессов из _active_workers"""
        dead_keys = []
        for key, proc in list(self._active_workers.items()):
            if proc.poll() is not None:
                dead_keys.append(key)
        
        for key in dead_keys:
            self._active_workers.pop(key, None)

    def close(self, modules: Optional[Union["RemoteModule", str, List[Union["RemoteModule", str]]]] = None):
        """
        Остановить процессы.

        :param modules: None (все), RemoteModule, str или список из них
        """
        if modules is None:
            call_ids_to_kill = list(self._active_workers.keys())
        else:
            if not isinstance(modules, list):
                modules = [modules]

            call_ids_to_kill = []

            for item in modules:
                # нормализация
                if hasattr(item, '_module_name'):  # Это RemoteModule
                    item = item._module_name
                else:
                    item = str(item)

                # 1. точное совпадение (stateful: module)
                if item in self._active_workers:
                    call_ids_to_kill.append(item)
                    continue

                # 2. если указали module.func (stateless)
                if "." in item:
                    if item in self._active_workers:
                        call_ids_to_kill.append(item)
                    continue

                # 3. fallback: убить все функции модуля (stateless случай)
                prefix = item + "."
                for key in self._active_workers.keys():
                    if key.startswith(prefix):
                        call_ids_to_kill.append(key)

        # завершение процессов
        for call_id in set(call_ids_to_kill):
            proc = self._active_workers.get(call_id)

            if proc:
                try:
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.close()
                except Exception:
                    pass

                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()

                self._active_workers.pop(call_id, None)
                self._dead_workers.append(call_id)

        self._cleanup_dead_workers()

    def get_functions(self, module_name):
        call_id = "introspect_" + module_name
        payload = {
            "call_id": call_id,
            "module": module_name,
            "pickle_protocol": self.pickle_protocol
        }

        proc = subprocess.Popen(
            [str(self.python), str(self.introspect_script), str(self.project_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        pickle.dump(payload, proc.stdin, protocol=self.pickle_protocol)
        proc.stdin.close()

        try:
            out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # Очистка буферов
            raise FailedIntrospectModule(
                module_name, self.project_dir,
                "Introspection timeout (30s)"
            )

        if err:
            raise FailedIntrospectModule(
                module_name, self.project_dir,
                err.decode("utf-8", errors="replace")
            )

        msg = pickle.loads(out)

        if msg["type"] == "INTROSPECTION" and msg["call_id"] == call_id:
            return msg["payload"]

        raise FailedIntrospectModule(module_name, self.project_dir, "Invalid introspection response")

    def call_function(
            self,
            module: str,
            func: str,
            type_output: str,
            stateful: bool,
            logger,
            caching: bool,
            timeout,
            *args,
            **kwargs
    ):
        caching_key = None
        if caching:
            caching_key = self.cache.make_key(module, func, *args, **kwargs)
            if self.cache.exists(caching_key):
                return self.cache.get(caching_key)

        call_id = str(uuid.uuid4())
        payload = {
            "call_id": call_id,
            "module": module,
            "function": func,
            "args": args,
            "kwargs": kwargs,
            "pickle_protocol": self.pickle_protocol,
            "stream_threshold": self.stream_threshold,
            "chunk_size": self.chunk_size
        }

        # Определяем ключ для _active_workers
        proc_key = module if stateful else f"{module}.{func}"

        # Очистка мёртвых процессов
        self._cleanup_dead_processes()

        proc = self._active_workers.get(proc_key)
        
        # Проверяем, жив ли процесс
        if proc and proc.poll() is not None:
            self._active_workers.pop(proc_key, None)
            proc = None

        if not proc:
            proc = subprocess.Popen(
                [str(self.python), str(self.worker_script), str(self.project_dir)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._active_workers[proc_key] = proc

        wd = Watchdog(proc, timeout.seconds, timeout.mode)

        try:
            try:
                pickle.dump(payload, proc.stdin, protocol=self.pickle_protocol)
                proc.stdin.flush()
            except BrokenPipeError:
                # Worker упал до чтения
                self._active_workers.pop(proc_key, None)
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except Exception:
                        proc.kill()
                raise RemoteExecutionError(
                    error_type="BrokenPipeError",
                    error_message="Worker process died before reading request",
                    remote_traceback=None
                )

            # В stateless режиме закрываем stdin после отправки
            if not stateful:
                proc.stdin.close()

            reader = MessageReader(proc.stdout, call_id, wd, module, func, self._dead_workers)

            while True:
                msg = next(reader)
                msg_type = msg["type"]

                if msg_type == "OUTPUT":
                    output_handler(msg, type_output, logger)
                elif msg_type == "YIELD":
                    return YieldIterator(reader, msg)
                elif msg_type == "URESULT":
                    return UReturnIterator(reader, msg).get()
                elif msg_type == "RESULT":
                    if caching_key:
                        self.cache.set(caching_key, msg["payload"])
                    return msg["payload"]
                elif msg_type == "DONE":
                    return None
                elif msg_type == "ERROR":
                    raise RemoteExecutionError(
                        error_type=msg["error_type"],
                        error_message=msg["error_msg"],
                        remote_traceback=msg.get("traceback"),
                    )
                else:
                    raise TypeMessageNotFound(msg_type)
        finally:
            # Останавливаем watchdog
            wd.stop()
            
            # В stateless режиме удаляем процесс после выполнения
            if not stateful and proc_key in self._active_workers:
                proc = self._active_workers.pop(proc_key)
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except Exception:
                        proc.kill()
