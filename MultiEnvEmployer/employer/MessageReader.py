import pickle

from MultiEnvEmployer.utils.errors import (
    RemoteTimeoutError,
    RemoteCloseFunction
)


class MessageReader:
    def __init__(self, stdout_pipe, call_id, watchdog, module, func, dead_workers):
        self.stdout_pipe = stdout_pipe
        self.call_id = call_id
        self.watchdog = watchdog
        self.module = module
        self.func = func
        self.dead_workers = dead_workers

    def __iter__(self):
        return self

    def __next__(self):
        try:
            while True:
                msg = pickle.load(self.stdout_pipe)

                if msg.get("call_id") != self.call_id:
                    continue

                self.watchdog.poke()
                return msg
        except EOFError:
            if self.watchdog.timed_out:
                raise RemoteTimeoutError(
                    self.call_id,
                    self.watchdog.timeout_mode,
                    self.watchdog.timeout_seconds,
                    self.watchdog.last_progress
                )
            elif self.module + "." + self.func in self.dead_workers:
                self.dead_workers.remove(self.module + "." + self.func)
                raise RemoteCloseFunction(
                    self.module,
                    self.func
                )
            raise
