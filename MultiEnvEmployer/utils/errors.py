from typing import Optional


class MultiEnvEmployerError(Exception):
    """
    Базовый класс всех исключений библиотеки MultiEnvEmployer.

    Используется как общий предок для ошибок,
    возникающих в процессе взаимодействия с удалёнными
    окружениями, воркерами и служебной инфраструктурой.

    Подавляет автоматическое связывание исключений,
    чтобы внутренние ошибки реализации не «протекали»
    в публичный API библиотеки.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.__suppress_context__ = True


class RemoteError(MultiEnvEmployerError):
    """
    Базовое исключение для ошибок, связанных
    с удалённым выполнением, удалёнными воркерами
    и обменом данными между процессами.
    """
    pass


class RemoteTimeoutError(RemoteError):
    """
    Исключение выбрасывается, когда удалённый вызов
    превышает установленное время ожидания.

    Содержит информацию о идентификаторе вызова, режиме
    тайм-аута, установленном лимите времени и последнем
    прогрессе выполнения (если доступен). Используется
    для информирования о зависании или долгой работе
    удалённого процесса.
    """

    def __init__(
        self,
        call_id: str,
        timeout_mode: str,
        timeout_seconds: float,
        last_progress: Optional[str] = None
    ):
        self.call_id = call_id
        self.timeout_mode = timeout_mode
        self.timeout_seconds = timeout_seconds
        self.last_progress = last_progress

        message = (
            f"Remote call '{call_id}' timed out "
            f"(mode={timeout_mode}, timeout={timeout_seconds}s)"
        )
        if last_progress is not None:
            message += f", last progress: {last_progress}"

        super().__init__(message)


class RemoteCloseFunction(RemoteError):
    """
    Исключение выбрасывается, когда удалённая функция
    принудительно завершает своё выполнение.

    Используется для информирования прокси и вызывающего кода,
    что функция была прервана до завершения и дальнейшее
    получение результата невозможно.
    """

    def __init__(self, module: Optional[str] = None, function: Optional[str] = None, reason: Optional[str] = None):
        self.module = module
        self.function = function
        self.reason = reason

        message = "Remote function was closed before completion"
        if module and function:
            message += f" ({module}.{function})"
        if reason:
            message += f": {reason}"

        super().__init__(message)


class TypeMessageNotFound(RemoteError):
    """
    Исключение выбрасывается, когда от удалённого воркера
    получено сообщение с неизвестным типом.

    Такая ошибка указывает на нарушение протокола обмена
    данными, рассинхронизацию версий или повреждение
    передаваемого сообщения.
    """

    def __init__(self, message_type: str):
        self.message_type = message_type
        super().__init__(
            f"Unknown remote message type: {message_type}"
        )


class FailedIntrospectModule(RemoteError):
    """
    Исключение выбрасывается, когда не удаётся получить
    информацию о функциях удалённого модуля
    в процессе его интроспекции.

    Ошибка может возникать из-за сбоя удалённого воркера,
    ошибки запуска служебного процесса или некорректного
    формата ответа.
    """

    def __init__(
        self,
        module: str,
        project_dir: Optional[str] = None,
        reason: Optional[str] = None
    ):
        self.module = module
        self.project_dir = project_dir
        self.reason = reason

        message = f"Failed to introspect remote module '{module}'"
        if project_dir:
            message += f", project_dir '{project_dir}'"
        if reason:
            message += f": {reason}"

        super().__init__(message)


class RemoteFunctionNotFound(RemoteError):
    """
    Исключение выбрасывается при попытке доступа
    к функции, отсутствующей в экспортируемом
    интерфейсе удалённого модуля.

    Возникает на стороне прокси до выполнения
    удалённого вызова и обычно указывает
    на ошибку имени функции или несовпадение
    версий модуля.
    """

    def __init__(self, module: str, function: str):
        self.module = module
        self.function = function

        super().__init__(
            f"Remote module '{module}' has no function '{function}'"
        )


class RemoteExecutionError(RemoteError):
    """
    Исключение, представляющее ошибку, произошедшую
    при выполнении кода на удалённой стороне.

    Используется для передачи информации об исключении,
    возникшем в удалённом воркере, включая тип ошибки,
    сообщение и traceback удалённого процесса.
    """

    def __init__(
        self,
        error_type: str,
        error_message: str,
        remote_traceback: Optional[str] = None,
    ):
        self.error_type = error_type
        self.error_message = error_message
        self.remote_traceback = remote_traceback

        message = f"Remote exception {error_type}: {error_message}"
        if remote_traceback:
            message += f"\nRemote traceback:\n{remote_traceback}"

        super().__init__(message)


class WrongArgumentsError(MultiEnvEmployerError):
    """
    Исключение выбрасывается, когда переданные аргументы
    не соответствуют сигнатуре удалённой функции.

    Используется при локальной валидации аргументов
    перед выполнением удалённого вызова и позволяет
    обнаружить ошибку без обращения к удалённому воркеру.
    """

    def __init__(
        self,
        module: str,
        function: str,
        details: Optional[str] = None,
    ):
        self.module = module
        self.function = function
        self.details = details

        message = f"Wrong arguments for remote function {module}.{function}"
        if details:
            message += f": {details}"

        super().__init__(message)


class LoggerNotFound(MultiEnvEmployerError):
    """
    Исключение выбрасывается, когда выбран режим вывода,
    требующий использования логгера, но логгер
    не был передан или равен None.

    Используется в случаях, когда параметр type_output
    предполагает логирование (например: 'logger'
    или 'terminal|logger').
    """

    def __init__(self, output_type: str, context: Optional[str] = None):
        self.output_type = output_type
        self.context = context

        message = (
            f"Logger is required for output type '{output_type}', "
            f"but was not provided."
        )
        if context:
            message += f" Context: {context}."

        super().__init__(message)
