import sys
import io
import importlib
import pickle
import inspect
import traceback
from pathlib import Path

DEFAULT_PICKLE_PROTOCOL = 4
STREAM_THRESHOLD = 1024 * 1024  # 1 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB

try:
    import numpy as _np
    NUMPY_D = True
except Exception:
    _np = None
    NUMPY_D = False


project_dir = sys.argv[1]
project_path = Path(project_dir)

if not project_path.exists():
    sys.stderr.write(f"Error: project_dir does not exist: {project_dir}\n")
    sys.exit(1)

if not project_path.is_dir():
    sys.stderr.write(f"Error: project_dir is not a directory: {project_dir}\n")
    sys.exit(1)

if str(project_path) not in sys.path:
    sys.path.insert(0, str(project_path))


def is_streamable(obj):
    if isinstance(obj, str):
        return True

    if isinstance(obj, (list, tuple)):
        return True

    if NUMPY_D and isinstance(obj, _np.ndarray):
        return True

    return False


def send_result_or_stream(result, call_id, pickle_protocol, threshold=STREAM_THRESHOLD, chunk_size=CHUNK_SIZE):
    """
    Сериализует результат и отправляет либо целиком, либо чанками.
    Избегает двойной сериализации.
    """
    if not is_streamable(result):
        # Не поддерживает streaming - отправляем как есть
        send({"call_id": call_id, "type": "RESULT", "payload": result}, pickle_protocol)
        return
    
    try:
        data = pickle.dumps(result, protocol=pickle_protocol)
    except Exception:
        # Если не сериализуется - пробуем отправить как есть
        send({"call_id": call_id, "type": "RESULT", "payload": result}, pickle_protocol)
        return
    
    if len(data) <= threshold:
        # Маленький объект - отправляем целиком через RESULT
        send({"call_id": call_id, "type": "RESULT", "payload": result}, pickle_protocol)
    else:
        # Большой объект - отправляем чанками через URESULT
        data_view = memoryview(data)
        total_size = len(data)
        seq = 0
        
        for i in range(0, total_size, chunk_size):
            chunk = bytes(data_view[i:i+chunk_size])
            send({
                "call_id": call_id,
                "type": "URESULT",
                "payload": chunk,
                "seq": seq,
                "is_last": i+chunk_size >= total_size
            }, pickle_protocol)
            seq += 1


class StdoutInterceptor(io.StringIO):
    def __init__(self, call_id, send_func, pickle_protocol):
        super().__init__()
        self.call_id = call_id
        self.send_func = send_func
        self.pickle_protocol = pickle_protocol

    def write(self, s):
        if s.strip():
            self.send_func({
                "call_id": self.call_id,
                "type": "OUTPUT",
                "payload": s
            }, self.pickle_protocol)
        return len(s)

    def flush(self):
        pass


def send(msg, pickle_protocol=DEFAULT_PICKLE_PROTOCOL):
    pickle.dump(msg, sys.__stdout__.buffer, protocol=pickle_protocol)
    sys.__stdout__.buffer.flush()


def execute_call(module_name, func_name, args, kwargs, call_id, pickle_protocol, stream_threshold=STREAM_THRESHOLD, chunk_size=CHUNK_SIZE):
    try:
        module = importlib.import_module(module_name)

        func = getattr(module, func_name)
        old_stdout = sys.stdout
        sys.stdout = StdoutInterceptor(call_id, send, pickle_protocol)
        try:
            result = func(*args, **kwargs)
            
            # Обработка async coroutine
            if inspect.iscoroutine(result):
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                if loop is None:
                    result = asyncio.run(result)
                else:
                    # Если loop уже запущен, используем его
                    result = loop.run_until_complete(result)
            
            # Обработка async generator
            elif inspect.isasyncgen(result):
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                async def consume_async_gen():
                    async for item in result:
                        send({"call_id": call_id, "type": "YIELD", "payload": item}, pickle_protocol)
                
                loop.run_until_complete(consume_async_gen())
                send({"call_id": call_id, "type": "DONE"}, pickle_protocol)
                return
                
        finally:
            sys.stdout = old_stdout

        if inspect.isgenerator(result):
            for item in result:
                send({"call_id": call_id, "type": "YIELD", "payload": item}, pickle_protocol)
            send({"call_id": call_id, "type": "DONE"}, pickle_protocol)
        else:
            send_result_or_stream(result, call_id, pickle_protocol, stream_threshold, chunk_size)
            send({"call_id": call_id, "type": "DONE"}, pickle_protocol)

    except Exception as e:
        # Логируем в stderr для отладки
        sys.stderr.write(f"Worker error in {module_name}.{func_name}: {type(e).__name__}: {str(e)}\n")
        send({
            "call_id": call_id,
            "type": "ERROR",
            "error_type": type(e).__name__,
            "error_msg": str(e),
            "traceback": traceback.format_exc()
        }, pickle_protocol)


if __name__ == "__main__":
    while True:
        try:
            payload = pickle.load(sys.stdin.buffer)
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        pickle_protocol = payload.get("pickle_protocol", DEFAULT_PICKLE_PROTOCOL)
        stream_threshold = payload.get("stream_threshold", STREAM_THRESHOLD)
        chunk_size = payload.get("chunk_size", CHUNK_SIZE)

        execute_call(
            payload["module"],
            payload["function"],
            payload.get("args", ()),
            payload.get("kwargs", {}),
            payload["call_id"],
            pickle_protocol,
            stream_threshold,
            chunk_size
        )
