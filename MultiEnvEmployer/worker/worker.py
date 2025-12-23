import sys
import io
import importlib
import pickle
import inspect
import traceback

PICKLE_PROTOCOL = 4
STREAM_THRESHOLD = 1024 * 1024  # 1 MB
CHUNK_SIZE = 1024 * 1024        # 1 MB

try:
    import numpy as _np
    NUMPY_D = True
except Exception:
    _np = None
    NUMPY_D = False


project_dir = sys.argv[1]
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)


def is_streamable(obj):
    if isinstance(obj, str):
        return True

    if isinstance(obj, (list, tuple)):
        return True

    if NUMPY_D and isinstance(obj, _np.ndarray):
        return True

    return False


def large(obj, threshold=STREAM_THRESHOLD):  # 1 МБ по умолчанию
    """
    Определяет, большой ли объект для потоковой передачи.
    """
    try:
        size = len(pickle.dumps(obj, protocol=PICKLE_PROTOCOL))
        return size > threshold
    except Exception:
        # если не сериализуем — лучше сразу потоковый ULTRARESULT
        return True


def send_large_result(result, call_id, chunk_size=CHUNK_SIZE):
    data = pickle.dumps(result, protocol=PICKLE_PROTOCOL)
    seq = 0
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        send({
            "call_id": call_id,
            "type": "URESULT",
            "payload": chunk,
            "seq": seq,
            "is_last": i+chunk_size >= len(data)
        })
        del chunk
        seq += 1
    del data


class StdoutInterceptor(io.StringIO):
    def __init__(self, call_id, send_func):
        super().__init__()
        self.call_id = call_id
        self.send_func = send_func

    def write(self, s):
        if s.strip():  # не отправлять пустые строки
            self.send_func({
                "call_id": self.call_id,
                "type": "OUTPUT",
                "payload": s
            })
        return len(s)

    def flush(self):
        pass


def send(msg):
    # всегда пишем в настоящий stdout, который поддерживает buffer
    pickle.dump(msg, sys.__stdout__.buffer, protocol=PICKLE_PROTOCOL)
    sys.__stdout__.buffer.flush()


def execute_call(module_name, func_name, args, kwargs, call_id):
    try:
        module = importlib.import_module(module_name)

        func = getattr(module, func_name)
        old_stdout = sys.stdout
        sys.stdout = StdoutInterceptor(call_id, send)
        try:
            result = func(*args, **kwargs)
            if inspect.iscoroutine(result):
                import asyncio
                result = asyncio.run(result)
        finally:
            sys.stdout = old_stdout

        if inspect.isgenerator(result):
            for item in result:
                send({"call_id": call_id, "type": "YIELD", "payload": item})
            send({"call_id": call_id, "type": "DONE"})
        elif is_streamable(result) and large(result):
            send_large_result(result, call_id)
            send({"call_id": call_id, "type": "DONE"})
        else:
            send({"call_id": call_id, "type": "RESULT", "payload": result})
            send({"call_id": call_id, "type": "DONE"})

    except Exception as e:
        send({
            "call_id": call_id,
            "type": "ERROR",
            "error_type": type(e).__name__,
            "error_msg": str(e),
            "traceback": traceback.format_exc()
        })


if __name__ == "__main__":
    payload = pickle.load(sys.stdin.buffer)
    try:
        PICKLE_PROTOCOL = payload["picle_protocol"]
    except Exception:
        pass
    execute_call(
        payload["module"],
        payload["function"],
        payload.get("args", ()),
        payload.get("kwargs", {}),
        payload["call_id"]
    )
