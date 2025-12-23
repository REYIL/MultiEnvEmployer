from MultiEnvEmployer.utils.errors import (
    TypeMessageNotFound,
    RemoteExecutionError
)


class YieldIterator:
    def __init__(self, reader, first_msg):
        self.reader = reader
        self.first_msg = first_msg

    def __iter__(self):
        return self

    def __next__(self):
        if self.first_msg is not None:
            msg = self.first_msg
            self.first_msg = None
        else:
            msg = next(self.reader)

        msg_type = msg["type"]

        if msg_type == "YIELD":
            return msg["payload"]
        elif msg_type == "DONE":
            raise StopIteration
        elif msg_type == "ERROR":
            raise RemoteExecutionError(
                error_type=msg["error_type"],
                error_message=msg["error_msg"],
                remote_traceback=msg.get("traceback"),
            )
        else:
            raise TypeMessageNotFound(msg_type)
