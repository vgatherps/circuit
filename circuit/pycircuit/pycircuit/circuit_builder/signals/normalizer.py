from dataclasses import dataclass

from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.component import Component, HasOutput


@dataclass
class Normalizer:
    def __init__(self, normalize: HasOutput):

        circuit = CircuitContextManager.active_circuit()

        self._normalize = normalize

        self._mean = circuit.summarize(normalize, "mean")
        self._std = circuit.summarize(normalize, "std")

    def normalize(self, input: HasOutput) -> Component:
        return (input - self._mean) / self._std

    def denormalize(self, input: HasOutput) -> Component:
        return (input * self._std) + self._mean

    @property
    def mean(self) -> Component:
        return self._mean

    @property
    def std(self) -> Component:
        return self._std
