from typing import Dict, List

from pycircuit.circuit_builder.circuit import CallGroup

INPUT_STR_NAME = "__name__"
LOAD_CALL_TYPE = "TriggerCall"


def generate_lookup_of(call_name: str, prefix="") -> str:
    return f"""if ("{call_name}" == {INPUT_STR_NAME}) {{
return &{prefix}{call_name};
}}"""


def generate_load_call_signature(struct_name: str, prefix="", postfix="") -> str:

    return (
        f"{prefix}{LOAD_CALL_TYPE}<{prefix}InputTypes::{struct_name}> {prefix}do_lookup_trigger"
        f"(const std::string &{INPUT_STR_NAME}, InputTypes::{struct_name} **){postfix}"
    )


def general_load_call(groups: Dict[str, CallGroup], struct_name: str, prefix="") -> str:

    for group in groups.values():
        assert group.struct == struct_name

    ordered_groups = sorted(groups.keys())

    check_lines = "\n\n".join(
        generate_lookup_of(call_name, prefix=prefix) for call_name in ordered_groups
    )

    return f"""{generate_load_call_signature(struct_name, prefix=prefix)} {{

{check_lines}

throw std::runtime_error(std::string("No calls matched the given name ") + {INPUT_STR_NAME});}}"""


def generate_all_load_call_signatures(
    groups: Dict[str, CallGroup], prefix="", postfix=""
) -> str:
    all_structs = sorted(set(group.struct for group in groups.values()))
    return "\n\n".join(
        generate_load_call_signature(struct, prefix=prefix, postfix=postfix)
        for struct in all_structs
    )


def general_all_load_call_bodies(groups: Dict[str, CallGroup], prefix="") -> str:
    all_structs = sorted(set(group.struct for group in groups.values()))

    all_calls = []

    for struct in all_structs:
        subset = {
            call: group for (call, group) in groups.items() if group.struct == struct
        }

        all_calls.append(general_load_call(subset, struct, prefix=prefix))

    return "\n\n".join(all_calls)


def generate_top_level_loader(groups: Dict[str, CallGroup]) -> str:
    all_structs = sorted(set(group.struct for group in groups.values()))

    struct_requires = " || ".join(
        f"std::is_same_v<InputTypes::{struct}, T>" for struct in all_structs
    )

    return f"""template<class T>
requires ({struct_requires})
{LOAD_CALL_TYPE}<T> lookup_trigger(const std::string &name) {{
return do_lookup_trigger(name, (T **)nullptr);}}"""
