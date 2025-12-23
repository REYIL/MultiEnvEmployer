import inspect
import logging

from MultiEnvEmployer.utils.errors import (
    RemoteFunctionNotFound,
    WrongArgumentsError
)
from MultiEnvEmployer.employer.OutputHandler import output_mods
from MultiEnvEmployer.employer.Watchdog import timeout_mods
from MultiEnvEmployer.employer.employer import Employer


def _make_signature(sig_str: str) -> inspect.Signature:
    """Создаём inspect.Signature из строки вида '(a, b=1, c: int=2)'."""
    src = f"def _dummy{sig_str}: pass"
    ns = {}
    exec(src, ns)
    func = ns["_dummy"]
    return inspect.signature(func)


class _RemoteMeta:
    def __init__(self, mod):
        self._mod = mod

    @property
    def functions(self):
        return self._mod._functions


class RemoteFunction:
    __slots__ = (
        "module",
        "name",
        "_employer",
        "_type_output",
        "_logger",
        "_caching",
        "_timeout_seconds",
        "_timeout_mode",
        "_signature",
    )

    def __init__(
        self,
        employer,
        module,
        name,
        signature,
        type_output,
        logger,
        caching,
        timeout_seconds,
        timeout_mode,
    ):
        self._employer = employer
        self.module = module
        self.name = name
        self._signature = signature
        self._type_output = type_output
        self._logger = logger
        self._caching = caching
        self._timeout_seconds = timeout_seconds
        self._timeout_mode = timeout_mode

    def __call__(self, *args, **kwargs):
        if self._signature:
            try:
                self._signature.bind(*args, **kwargs)
            except TypeError as e:
                raise WrongArgumentsError(
                    module=self.module,
                    function=self.name,
                    details=str(e),
                )

        return self._employer.call_function(
            self.module,
            self.name,
            self._type_output,
            self._logger,
            self._caching,
            self._timeout_seconds,
            self._timeout_mode,
            *args,
            **kwargs
        )

    def __repr__(self):
        return f"{self.module}.{self.name}"

    def __str__(self):
        return f"{self.module}.{self.name}"


class RemoteModule:
    def __init__(
        self,
        employer: Employer,
        module_name: str,
        type_output: output_mods = "terminal",
        logger: logging.Logger = None,
        caching: bool = False,
        timeout_seconds: int = 60,
        timeout_mode: timeout_mods = "progress"
    ):
        self._employer = employer
        self._module_name = module_name
        self._type_output = type_output
        self._logger = logger
        self._caching = caching
        self._timeout_seconds = timeout_seconds
        self._timeout_mode = timeout_mode

        self._functions = self._employer.get_functions(self._module_name)
        self._signatures = self._build_signatures()

    @property
    def __remote__(self):
        return _RemoteMeta(self)

    def _build_signatures(self):
        signatures = {}
        for name, meta in self._functions.items():
            try:
                signatures[name] = _make_signature(meta["signature"])
            except Exception:
                signatures[name] = None
        return signatures

    def __getattr__(self, name):
        if name not in self._functions:
            raise RemoteFunctionNotFound(self._module_name, name)

        return RemoteFunction(
            employer=self._employer,
            module=self._module_name,
            name=name,
            signature=self._signatures.get(name),
            type_output=self._type_output,
            logger=self._logger,
            caching=self._caching,
            timeout_seconds=self._timeout_seconds,
            timeout_mode=self._timeout_mode,
        )

    def __repr__(self):
        return f"<RemoteModule {self._module_name}>"
