import os
import sys
import subprocess
import uuid
import pickle
from typing import Union

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


class Employer:
    def __init__(
            self,
            project_dir: str,
            venv_path: str,
            picle_protocol: int = 4
    ):
        self.project_dir = project_dir
        self.python = os.path.join(
            venv_path, "Scripts" if sys.platform == "win32" else "bin", "python"
        )
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.worker_script = os.path.join(base_dir, "worker", "worker.py")
        self.introspect_script = os.path.join(base_dir, "worker", "introspection.py")

        self.picle_protocol = picle_protocol
        self._active_workers = {}
        self._dead_workers = []
        self.cache = FileCache(app_name="MultiEnvEmployer", version=None, max_items=50, picle_protocol=picle_protocol)

    def cache_clear(self):
        """Функция отчистки кэша"""
        self.cache.clear()

    def close(self, module_func: Union[str, list, None] = None):
        if module_func is None:
            call_ids_to_kill = list(self._active_workers.keys())
        elif not isinstance(module_func, list):
            call_ids_to_kill = [module_func]
        else:
            call_ids_to_kill = module_func

        for call_id in call_ids_to_kill:
            call_id = str(call_id)
            proc = self._active_workers.get(call_id)
            if proc and proc.poll() is None:
                proc.terminate()  # мягко
                proc.wait(timeout=5)
                self._active_workers.pop(call_id, None)
                self._dead_workers.append(call_id)

    def get_functions(self, module_name):
        call_id = "introspect_" + module_name
        payload = {
            "call_id": call_id,
            "module": module_name,
            "picle_protocol": self.picle_protocol
        }

        proc = subprocess.Popen(
            [self.python, self.introspect_script, self.project_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        pickle.dump(payload, proc.stdin, protocol=self.picle_protocol)
        proc.stdin.close()

        out, err = proc.communicate()
        if err:
            raise FailedIntrospectModule(
                module_name, self.project_dir,
                err.decode(errors="replace")
            )

        msg = pickle.loads(out)

        if msg["type"] == "INTROSPECTION" and msg["call_id"] == call_id:
            return msg["payload"]

        raise FailedIntrospectModule(module_name, self.project_dir, "Invalid introspection response")

    def call_function(self, module, func, type_output, logger, caching, timeout_seconds, timeout_mode, *args, **kwargs):
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
            "picle_protocol": self.picle_protocol
        }

        proc = subprocess.Popen(
            [self.python, self.worker_script, self.project_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self._active_workers[module + "." + func] = proc

        wd = Watchdog(proc, timeout_seconds, timeout_mode)

        pickle.dump(payload, proc.stdin, protocol=self.picle_protocol)
        proc.stdin.flush()

        reader = MessageReader(proc.stdout, call_id, wd, module, func, self._dead_workers)

        try:
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
            self._active_workers.pop(call_id, None)
