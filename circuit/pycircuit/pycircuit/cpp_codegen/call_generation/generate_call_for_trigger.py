from typing import Set

from pycircuit.circuit_builder.circuit import Circuit
from pycircuit.cpp_codegen.call_generation.call_metadata import CallMetaData
from pycircuit.cpp_codegen.call_generation.find_children_of import find_all_children_of
from pycircuit.cpp_codegen.call_generation.generate_single_call import (
    generate_single_call,
)


def generate_calls_for(meta: CallMetaData, circuit: Circuit) -> str:

    children_for_call = find_all_children_of(meta.triggered, circuit)
    all_children = "\n".join(
        generate_single_call(meta, component) for component in children_for_call
    )

    return f"""
    void {meta.call_name}() {{
        auto *__restrict {meta.own_self_name} = this;
        {all_children}
    }}
    """
    pass
