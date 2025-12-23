import threading
import time
from typing import Literal

timeout_mods = Literal["none", "absolute", "progress"]


class Watchdog:
    def __init__(self, proc, timeout_seconds: float, timeout_mode: timeout_mods):
        self.proc = proc
        self.timeout_seconds = timeout_seconds
        self.timeout_mode = timeout_mode
        self.start_time = time.time()
        self.last_progress = self.start_time
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._timed_out = False

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self._stop_event.is_set():
            time.sleep(0.1)  # небольшая задержка, чтобы не грузить CPU
            now = time.time()

            if self.timeout_mode == "none":
                continue

            if self.timeout_mode in ("absolute",):
                if now - self.start_time > self.timeout_seconds:
                    self._timed_out = True
                    self._kill_worker()
                    break

            if self.timeout_mode in ("progress",):
                with self._lock:
                    last_progress = self.last_progress
                if now - last_progress > self.timeout_seconds:
                    self._timed_out = True
                    self._kill_worker()
                    break

    def poke(self):
        """Вызывается при любом прогрессе: OUTPUT, YIELD, RESULT, DONE"""
        with self._lock:
            self.last_progress = time.time()

    def stop(self):
        self._stop_event.set()
        self.thread.join(timeout=0.1)

    def _kill_worker(self):
        try:
            self.proc.kill()
        except Exception:
            pass  # worker уже мог завершиться

    @property
    def timed_out(self):
        return self._timed_out
