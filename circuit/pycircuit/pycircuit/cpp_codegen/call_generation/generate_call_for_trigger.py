from typing import Set

from pycircuit.circuit_builder.circuit import Circuit
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.ephemeral import is_ephemeral
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_single_call import (
    generate_single_call,
)


def generate_calls_for(
    meta: CallMetaData, circuit: Circuit, non_ephemeral_components: Set[str]
) -> str:

    children_for_call = find_all_children_of(meta.triggered, circuit)
    all_children = "\n".join(
        generate_single_call(component, circuit, non_ephemeral_components)
        for component in children_for_call
    )

    return f"""
    void {meta.call_name}() {{
        {all_children}
    }}
    """
    pass
