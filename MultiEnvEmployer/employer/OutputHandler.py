from typing import Literal

from MultiEnvEmployer.utils.errors import LoggerNotFound

output_mods = Literal["terminal", "logger", "terminal|logger", "none"]


def output_handler(msg, type_output: output_mods = "terminal", logger=None):
    text = msg.get("payload", "")
    
    if type_output == "none":
        return
    elif type_output == "terminal":
        print(text)
    elif type_output == "logger":
        if logger is None:
            raise LoggerNotFound(
                output_type=type_output,
                context="output_handler"
            )
        logger.info(text)
    elif type_output == "terminal|logger":
        if logger is None:
            raise LoggerNotFound(
                output_type=type_output,
                context="output_handler"
            )
        print(text)
        logger.info(text)
