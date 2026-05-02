import sys
import importlib
import pickle
import inspect
from pathlib import Path

PICKLE_PROTOCOL = 4

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


def send(msg):
    pickle.dump(msg, sys.__stdout__.buffer, protocol=PICKLE_PROTOCOL)
    sys.__stdout__.buffer.flush()


def introspect_module(module_name):
    module = importlib.import_module(module_name)
    functions = {}
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        functions[name] = {
            "signature": str(inspect.signature(obj)),
            "doc": inspect.getdoc(obj),
        }
    return functions


if __name__ == "__main__":
    payload = pickle.load(sys.stdin.buffer)
    functions_meta = introspect_module(payload["module"])
    try:
        PICKLE_PROTOCOL = payload["pickle_protocol"]
    except Exception:
        pass
    send({
        "call_id": payload["call_id"],
        "type": "INTROSPECTION",
        "payload": functions_meta
    })
