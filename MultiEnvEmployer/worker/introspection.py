import sys
import importlib
import pickle
import inspect

PICKLE_PROTOCOL = 4

project_dir = sys.argv[1]
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)


def send(msg):
    # всегда пишем в настоящий stdout, который поддерживает buffer
    pickle.dump(msg, sys.__stdout__.buffer, protocol=PICKLE_PROTOCOL)
    sys.__stdout__.buffer.flush()


def introspect_module(module_name):
    module = importlib.import_module(module_name)
    functions = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        # можно добавить сигнатуры и docstring
        functions[name] = {
            "signature": str(inspect.signature(obj)),
            "doc": inspect.getdoc(obj),
        }
    return functions


if __name__ == "__main__":
    payload = pickle.load(sys.stdin.buffer)
    functions_meta = introspect_module(payload["module"])
    try:
        PICKLE_PROTOCOL = payload["picle_protocol"]
    except Exception:
        pass
    send({
        "call_id": payload["call_id"],
        "type": "INTROSPECTION",
        "payload": functions_meta
    })
