from typing import List

from pycircuit.circuit_builder.circuit import Component

from pycircuit.pycircuit.cpp_codegen.call_metadata import CallMetaData


def get_type_data_for(meta: CallMetaData, component: Component) -> List[str]:

    sorted_by_idx = sorted(component.inputs.values(), key=lambda x: x.input_idx)

    input_names = [
        f"{meta.own_self_name}->outputs.{c.parent}.{c.output_name}"
        for c in sorted_by_idx
    ]

    return [
        f"using {c.input_idx}_T = decltype({name});"
        for (c, name) in zip(sorted_by_idx, input_names)
    ]
