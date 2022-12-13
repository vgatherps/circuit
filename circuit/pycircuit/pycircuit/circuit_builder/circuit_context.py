"""
This file contains the context management code for pycircuit.

For simplicity, this code IS NOT reentrant. Do not mix with async or threads,
if there's a need in the future then something here can be worked out
"""

from contextlib import AbstractContextManager
from types import TracebackType
from typing import List, Literal

from pycircuit.circuit_builder.circuit import CircuitBuilder

_CIRCUIT_STACK: List[CircuitBuilder] = []


class CircuitContextManager(AbstractContextManager):
    def __init__(self, circuit: CircuitBuilder):
        self._circuit = circuit

    def __enter__(self) -> "CircuitContextManager":
        global _CIRCUIT_STACK
        if _CIRCUIT_STACK:
            if _CIRCUIT_STACK[-1] is not self._circuit:
                raise RuntimeError("Multiple distinct circuits used in context manager")
        _CIRCUIT_STACK.append(self._circuit)
        return self

    def __exit__(
        self,
        __exc_type,
        __exc_value,
        __traceback,
    ) -> Literal[False]:
        global _CIRCUIT_STACK
        assert _CIRCUIT_STACK
        assert _CIRCUIT_STACK[-1] is self._circuit
        _CIRCUIT_STACK.pop()
        return False

    @property
    def circuit(self) -> CircuitBuilder:
        return self._circuit

    @staticmethod
    def active_circuit() -> CircuitBuilder:

        if not _CIRCUIT_STACK:
            raise RuntimeError("Active circuit requested outside of context")

        return _CIRCUIT_STACK[-1]
