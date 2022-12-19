from dataclasses import dataclass
from typing import List, Union


from pycircuit.circuit_builder.circuit import CallGroup
from pycircuit.circuit_builder.circuit import ComponentOutput
from pycircuit.circuit_builder.circuit import CircuitData


@dataclass
class EqLit:
    output: ComponentOutput
    eq_to: str


@dataclass
class EqValidOutput:
    output_a: ComponentOutput
    output_b: ComponentOutput


OutputCheck = Union[EqLit, EqValidOutput]


@dataclass
class TriggerVal:
    ctor: str
    name: str


@dataclass
class TriggerCall:
    values: List[TriggerVal]
    trigger: CallGroup
    call_name: str
    checks: List[OutputCheck]


@dataclass
class CircuitTest:
    calls: List[TriggerCall]
    circuit: CircuitData
