from pycircuit.circuit_builder.circuit import Component
from pycircuit.cpp_codegen.call_metadata import CallMetaData

# On one hand, having this largely rely on auto
# make the codegen easier.
#
# On the other, it introduces huge room for error esepcially around reference autoconversion


def generate_single_call(meta: CallMetaData, component: Component) -> str:
    # TODO static vs stateful
    # Maybe another todo impermanent (only exist within a single graph) vs stored?
    # TODO How to deal with generics? Can/should just do in order

    sorted_by_idx = sorted(component.inputs.values(), key=lambda x: x.input_idx)

    assert list(i.input_idx for i in sorted_by_idx) == list(
        range(0, len(sorted_by_idx))
    )

    input_names = [
        f"{meta.own_self_name}->outputs.{c.parent}.{c.output_name}"
        for c in sorted_by_idx
    ]

    all_decltypes = [
        f"using {c.input_idx}_T = decltype({name});"
        for (c, name) in zip(sorted_by_idx, input_names)
    ]

    all_values = [
        f"{t_name} &{c.input_name}_v = {name};"
        for (t_name, c, name) in zip(all_decltypes, sorted_by_idx, input_names)
    ]

    input_list = ",".join(f"{c.input_name}_v" for c in sorted_by_idx)
    output_name = f"{meta.own_self_name}->outputs.{component.name}"

    if component.definition.static_call:
        type_list = ",".join(all_decltypes)
        call_name = f"{component.definition.class_name}<{type_list}>::call({input_list}, {output_name})"
    else:
        object_name = f"{meta.own_self_name}->objects.{component.name}"
        call_name = f"{object_name}.call({input_list}, {output_name})"

    decltypes = "\n".join(all_decltypes)
    values = "\n".join(all_values)
    return f"""
    {{
        {decltypes}
        {values}
        {call_name}
    }}
    """
