from collections import OrderedDict
from dataclasses import dataclass
from typing import Set

from pycircuit.circuit_builder.circuit import Circuit, Component


@dataclass
class AnnotatedComponent:
    component: Component

    is_ephemeral: bool


@dataclass
class GenerationMetadata:
    non_ephemeral_components: Set[str]

    annotated_components: OrderedDict[str, AnnotatedComponent]
    circuit: Circuit
