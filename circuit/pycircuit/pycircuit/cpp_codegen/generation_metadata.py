from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Set

from pycircuit.circuit_builder.circuit import Circuit, Component


@dataclass
class NonEphemeralData:
    validity_index: int


@dataclass
class AnnotatedComponent:
    component: Component
    ephemeral_data: Optional[NonEphemeralData]

    @property
    def is_ephemeral(self) -> bool:
        return self.ephemeral_data is None


@dataclass
class GenerationMetadata:
    non_ephemeral_components: Set[str]
    annotated_components: OrderedDict[str, AnnotatedComponent]
    circuit: Circuit
