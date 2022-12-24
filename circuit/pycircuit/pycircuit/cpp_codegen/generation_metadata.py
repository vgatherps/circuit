from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from pycircuit.circuit_builder.circuit import (
    TIME_TYPE,
    CircuitData,
    Component,
    ComponentOutput,
)
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.ephemeral import (
    find_nonephemeral_outputs,
    is_ephemeral,
)
from pycircuit.cpp_codegen.call_generation.find_children_of import (
    CalledComponent,
    find_all_children_of,
    find_all_children_of_from_outputs,
)
from pycircuit.cpp_codegen.type_names import get_alias_for, get_type_name_for_input


TIME_VAR = "__time_var__"
STRUCT_VAR = "__struct_var_"
CALL_VAR = "__call__"

LOCAL_DATA_LOAD_PREFIX = """
// This forces all of the below pointers to be based on this
// as a result, when we pass __enforce_derived to the callback INSTEAD
// of this, the compiler knows that it can't hoist writes past the call.
// Now, unfortunately, we only want this to happen for read access.
// As far as we're concerned, modifying variables in the call is undefined.
// I only want the compiler to ensure writes happen before, but don't force
// the compiler to reload. Not sure if there's a well-defined way to do this.

auto  * __restrict __enforce_derived = this;
Externals  & __restrict _externals = __enforce_derived->externals;
Objects  &  __restrict _objects = __enforce_derived->objects;
auto & __restrict outputs_is_valid = __enforce_derived->outputs.is_valid;
"""

LOCAL_TIME_LOAD__PREFIX = f"""
this->update_time({TIME_VAR});
"""


@dataclass
class OutputMetadata:
    validity_index: Optional[int]
    is_value_ephemeral: bool


@dataclass
class AnnotatedComponent:
    component: Component
    output_data: Dict[str, OutputMetadata]
    call_root: str
    class_generics: str


@dataclass
class GenerationMetadata:
    circuit: CircuitData
    struct_name: str

    non_ephemeral_components: Set[ComponentOutput]
    annotated_components: OrderedDict[str, AnnotatedComponent]

    call_endpoints: List[CallMetaData]

    required_validity_markers: int


def get_ordered_generic_inputs(component: Component) -> List[str]:
    return sorted(
        component.definition.generics_order.keys(),
        key=lambda x: component.definition.generics_order[x],
    )


def generate_output_metadata_for(
    component: Component,
    all_non_ephemeral_outputs: Set[ComponentOutput],
    validity_market_count: int,
) -> Tuple[Dict[str, OutputMetadata], int]:
    pass
    output_metadata = {}
    for output in component.definition.outputs():
        ephemeral = is_ephemeral(component, output, all_non_ephemeral_outputs)
        always_valid = component.definition.d_output_specs[output].always_valid
        assume_invalid = component.definition.d_output_specs[output].assume_invalid
        if ephemeral or always_valid or assume_invalid:
            this_output_metadata = OutputMetadata(
                validity_index=None, is_value_ephemeral=ephemeral
            )
        else:
            this_output_metadata = OutputMetadata(
                validity_index=validity_market_count, is_value_ephemeral=ephemeral
            )
            validity_market_count += 1

        output_metadata[output] = this_output_metadata

    return output_metadata, validity_market_count


def generate_call_signature(meta: CallMetaData, circuit: CircuitData, prefix: str = ""):
    call = circuit.call_groups[meta.call_name]
    struct = call.struct

    return f"void {prefix}{meta.call_name}({TIME_TYPE} {TIME_VAR}, InputTypes::{struct} {STRUCT_VAR}, RawCall<const Circuit *> {CALL_VAR})"


def find_all_subgraphs(circuit: CircuitData) -> List[List[CalledComponent]]:
    called = []

    for call_group in circuit.call_groups.values():
        children = find_all_children_of(call_group.inputs, circuit)
        called.append(children)

    # find timer subgraphs

    for component in circuit.components.values():
        if component.definition.timer_callset is not None:
            timer_outputs = {
                component.output(out)
                for out in component.definition.timer_callset.outputs
            }
            timer_children = find_all_children_of_from_outputs(circuit, timer_outputs)
            called_component = CalledComponent(
                callset=component.definition.timer_callset, component=component
            )
            all_timer_calls = [called_component] + timer_children
            called.append(all_timer_calls)

    return called


def generate_global_metadata(
    circuit: CircuitData, call_metas: List[CallMetaData], struct_name: str
) -> GenerationMetadata:
    circuit.validate()
    all_non_ephemeral_component_outputs: Set[ComponentOutput] = set()

    all_subgraphs = find_all_subgraphs(circuit)

    for children in all_subgraphs:
        all_non_ephemeral_component_outputs |= find_nonephemeral_outputs(children)
    # TODO we must ALSO find everybody who could get observed as part of a timer callback
    # or mailbox, when the parent is not triggered

    # TODO really need to split this into a few steps
    # Step 1: Generate every possible subgraph
    # Step 2: Generate every possible metadata
    # Step 3: Annotate the components in each subgraph
    # Step 4: Hand off fore codegen-specific annotations
    # Step 5: Generate the actual calls for each component

    # We kindof sortof do that already, but it's a little shakey

    annotated_components = OrderedDict()

    validity_marker_count = 0

    for (name, component) in circuit.components.items():

        if component.definition.static_call:
            # TODO this is obviously wrong w.r.t. callsets
            call_root = f"{get_alias_for(component)}::"
        else:
            object_name = f"_objects.{component.name}"
            call_root = f"{object_name}."

        output_metadata, validity_marker_count = generate_output_metadata_for(
            component, all_non_ephemeral_component_outputs, validity_marker_count
        )

        if component.definition.generics_order:
            generic_types = [
                get_type_name_for_input(component, component.inputs[inp].input_name)
                for inp in get_ordered_generic_inputs(component)
            ]
            inner_generics = ",".join(generic_types)
            generics_str = f"<{inner_generics}>"
        else:
            generics_str = ""

        annotated_components[name] = AnnotatedComponent(
            component=component,
            output_data=output_metadata,
            call_root=call_root,
            class_generics=generics_str,
        )

    return GenerationMetadata(
        non_ephemeral_components=all_non_ephemeral_component_outputs,
        circuit=circuit,
        annotated_components=annotated_components,
        struct_name=struct_name,
        call_endpoints=call_metas,
        required_validity_markers=validity_marker_count,
    )
