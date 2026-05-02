from __future__ import annotations
import inspect
import logging
from dataclasses import dataclass
from typing import Optional

from MultiEnvEmployer.utils.errors import (
    RemoteFunctionNotFound,
    WrongArgumentsError
)
from MultiEnvEmployer.employer.OutputHandler import output_mods
from MultiEnvEmployer.employer.Watchdog import timeout_mods


@dataclass
class TimeoutPolicy:
    seconds: int = 60
    mode: timeout_mods = "progress"


def _make_signature(sig_str: str) -> Optional[inspect.Signature]:
    """Создаём inspect.Signature из строки вида '(a, b=1, c: int=2)'."""
    try:
        src = f"def _dummy{sig_str}: pass"
        ns = {}
        exec(src, ns)
        func = ns["_dummy"]
        return inspect.signature(func)
    except Exception:
        return None


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
        "_print_output",
        "_stateful",
        "_logger",
        "_caching",
        "_timeout",
        "_signature",
    )

    def __init__(
        self,
        employer,
        module,
        name,
        signature,
        print_output,
        stateful,
        logger,
        caching,
        timeout,
    ):
        self._employer = employer
        self.module = module
        self.name = name
        self._signature = signature
        self._print_output = print_output
        self._stateful = stateful
        self._logger = logger
        self._caching = caching
        self._timeout = timeout or TimeoutPolicy()

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
            self._print_output,
            self._stateful,
            self._logger,
            self._caching,
            self._timeout,
            *args,
            **kwargs
        )

    def __repr__(self):
        return f"<RemoteFunction {self.module}.{self.name}>"

    def __str__(self):
        return f"{self.module}.{self.name}"


class RemoteModule:
    def __init__(
            self,
            employer: "Employer",
            module_name: str,
            print_output: output_mods = "terminal",
            logger: logging.Logger = None,
            stateful: bool = False,
            caching: bool = False,
            timeout: Optional[TimeoutPolicy] = None,
        ):
        self._employer = employer
        self._module_name = module_name
        self._print_output = print_output
        self._stateful = stateful
        self._caching = caching
        self._logger = logger
        self._timeout = timeout or TimeoutPolicy()

        self._functions = self._employer.get_functions(self._module_name)
        self._signatures = self._build_signatures()

    @property
    def __remote__(self):
        return _RemoteMeta(self)

    def _build_signatures(self):
        signatures = {}
        for name, meta in self._functions.items():
            signatures[name] = _make_signature(meta["signature"])
        return signatures

    def __getattr__(self, name):
        if name not in self._functions:
            raise RemoteFunctionNotFound(self._module_name, name)

        return RemoteFunction(
            employer=self._employer,
            module=self._module_name,
            name=name,
            signature=self._signatures.get(name),
            print_output=self._print_output,
            stateful=self._stateful,
            logger=self._logger,
            caching=self._caching,
            timeout=self._timeout,
        )

    def __repr__(self):
        return f"<RemoteModule {self._module_name}>"

    def __str__(self):
        return f"{self._module_name}"
