from typing import Dict, List

from pycircuit.circuit_builder.circuit import CallGroup

INPUT_STR_NAME = "__name__"
INPUT_TYPEID_NAME = "__typeid__"
VOID_CALL_POSTFIX = "_void"
LOAD_CALL_TYPE = "TriggerCall"


def generate_lookup_of(call_name: str, type_name: str, prefix="", postfix="") -> str:
    return f"""\
if ("{call_name}" == {INPUT_STR_NAME}) {{
    const std::type_info &the_type = typeid(InputTypes::{type_name});
    if (the_type == {INPUT_TYPEID_NAME}) {{
        return (void *)&{prefix}{call_name}{postfix};
    }} else {{
        return WrongCallbackType {{
            .type=the_type
        }};
    }}
}}"""


def general_load_call_for_struct(
    groups: Dict[str, CallGroup], struct_name: str, prefix=""
) -> str:

    for group in groups.values():
        assert group.struct == struct_name

    ordered_groups = sorted(groups.keys())

    return "\n\n".join(
        generate_lookup_of(
            call_name, struct_name, prefix=prefix, postfix=VOID_CALL_POSTFIX
        )
        for call_name in ordered_groups
    )


def general_all_load_call_lines(groups: Dict[str, CallGroup], prefix="") -> str:
    all_structs = sorted(set(group.struct for group in groups.values()))

    all_calls = []

    for struct in all_structs:
        subset = {
            call: group for (call, group) in groups.items() if group.struct == struct
        }

        all_calls.append(general_load_call_for_struct(subset, struct, prefix=prefix))

    return "\n\n".join(all_calls)


def generate_true_loader_body(groups: Dict[str, CallGroup], prefix: str = "") -> str:
    load_lines = general_all_load_call_lines(groups, prefix=prefix)
    return f"""\
{load_lines}

return NoCallbackFound{{}};"""


def top_level_real_loader(prefix: str = "") -> str:
    return f"""\
RawDiscoveredCallback {prefix}do_real_call_lookup(
    const std::string &{INPUT_STR_NAME},
    const std::type_info &{INPUT_TYPEID_NAME}
)"""
