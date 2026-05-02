import pickle

from MultiEnvEmployer.utils.errors import (
    RemoteTimeoutError,
    RemoteCloseFunction,
    RemoteCloseModule
)


class MessageReader:
    def __init__(self, stdout_pipe, call_id, watchdog, module, func, dead_workers):
        self.stdout_pipe = stdout_pipe
        self.call_id = call_id
        self.watchdog = watchdog
        self.module = module
        self.func = func
        self.dead_workers = dead_workers
        self._finished = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._finished:
            raise StopIteration

        try:
            while True:
                msg = pickle.load(self.stdout_pipe)

                if msg.get("call_id") != self.call_id:
                    continue

                self.watchdog.poke()

                # Остановить watchdog при завершении
                if msg["type"] in ("DONE", "ERROR", "RESULT"):
                    self._finished = True
                    self.watchdog.stop()

                return msg

        except EOFError:
            self._finished = True
            self.watchdog.stop()

            if self.watchdog.timed_out:
                raise RemoteTimeoutError(
                    self.call_id,
                    self.watchdog.timeout_mode,
                    self.watchdog.timeout_seconds,
                    self.watchdog.last_progress
                )
            elif self.module + "." + self.func in self.dead_workers:
                self.dead_workers.remove(self.module + "." + self.func)
                raise RemoteCloseFunction(self.module, self.func)
            elif self.module in self.dead_workers:
                self.dead_workers.remove(self.module)
                raise RemoteCloseModule(self.module)
            raise
