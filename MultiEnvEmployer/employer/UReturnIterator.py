import pickle

from MultiEnvEmployer.utils.errors import (
    TypeMessageNotFound,
    RemoteExecutionError
)


class UReturnIterator:
    """
    Внутренний сборщик return-значения.

    Используется Employer'ом.
    Пользователь получает уже готовый объект.
    """
    def __init__(self, reader, first_msg):
        self.reader = reader
        self.first_msg = first_msg
        self.buffer = bytearray()
        self._value = None
        self._done = False

    def get(self):
        """
        Блокирующе собирает результат и возвращает его
        как обычный return.
        """
        if self._done:
            return self._value

        while True:
            if self.first_msg is not None:
                msg = self.first_msg
                self.first_msg = None
            else:
                msg = next(self.reader)

            msg_type = msg["type"]

            if msg_type == "URESULT":
                self.buffer.extend(msg["payload"])
                if msg.get("is_last", False):
                    self._value = pickle.loads(self.buffer)
                    self._done = True
                    return self._value

            elif msg_type == "DONE":
                self._done = True
                self._value = None
                return None

            elif msg_type == "ERROR":
                raise RemoteExecutionError(
                    error_type=msg["error_type"],
                    error_message=msg["error_msg"],
                    remote_traceback=msg.get("traceback"),
                )
            else:
                raise TypeMessageNotFound(msg_type)

    def __repr__(self):
        return repr(self.get())

    def __str__(self):
        return str(self.get())

    def __getattr__(self, item):
        return getattr(self.get(), item)
