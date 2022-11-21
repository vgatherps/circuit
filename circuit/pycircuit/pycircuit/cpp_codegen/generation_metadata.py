from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional, Set

from pycircuit.circuit_builder.circuit import CircuitData, Component
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.ephemeral import (
    find_required_inputs,
    is_ephemeral,
)
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of


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
    circuit: CircuitData
    struct_name: str

    non_ephemeral_components: Set[str]
    annotated_components: OrderedDict[str, AnnotatedComponent]

    call_endpoints: List[CallMetaData]


def generate_global_metadata(
    circuit: CircuitData, call_metas: List[CallMetaData], struct_name: str
) -> GenerationMetadata:
    all_non_ephemeral_components = set()

    for call in call_metas:
        children = find_all_children_of(call.triggered, circuit)
        all_non_ephemeral_components |= find_required_inputs(children)

    annotated_components = OrderedDict()

    non_ephemeral_count = 0

    for (name, component) in circuit.components.items():
        ephemeral = is_ephemeral(component, all_non_ephemeral_components)
        if ephemeral:
            ephemeral_data = None
        else:
            ephemeral_data = NonEphemeralData(validity_index=non_ephemeral_count)
            non_ephemeral_count += 1

        annotated_components[name] = AnnotatedComponent(
            component=component, ephemeral_data=ephemeral_data
        )

    return GenerationMetadata(
        non_ephemeral_components=all_non_ephemeral_components,
        circuit=circuit,
        annotated_components=annotated_components,
        struct_name=struct_name,
        call_endpoints=call_metas,
    )
