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
from pycircuit.cpp_codegen.type_names import get_alias_for, get_type_name_for_input


@dataclass
class NonEphemeralData:
    validity_index: int


@dataclass
class AnnotatedComponent:
    component: Component
    ephemeral_data: Optional[NonEphemeralData]
    call_path: str
    class_generics: str

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


def get_ordered_generic_inputs(component: Component) -> List[str]:
    return sorted(
        component.definition.generics_order.keys(),
        key=lambda x: component.definition.generics_order[x],
    )


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

        if component.definition.static_call:
            call_path = f"{get_alias_for(component)}::call"
        else:
            object_name = f"objects.{component.name}"
            call_path = f"{object_name}.call"

        if component.definition.generics_order:
            generic_types = [
                get_type_name_for_input(component, component.inputs[inp])
                for inp in get_ordered_generic_inputs(component)
            ]
            inner_generics = ",".join(generic_types)
            generics_str = f"<{inner_generics}>"
        else:
            generics_str = ""

        annotated_components[name] = AnnotatedComponent(
            component=component,
            ephemeral_data=ephemeral_data,
            call_path=call_path,
            class_generics=generics_str,
        )

    return GenerationMetadata(
        non_ephemeral_components=all_non_ephemeral_components,
        circuit=circuit,
        annotated_components=annotated_components,
        struct_name=struct_name,
        call_endpoints=call_metas,
    )
