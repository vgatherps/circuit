from typing import Dict, List

from pycircuit.circuit_builder.circuit import CallGroup

INPUT_STR_NAME = "__name__"
INPUT_TYPEID_NAME = "__typeid__"
VOID_CALL_POSTFIX = "_void"
LOAD_CALL_TYPE = "TriggerCall"


def generate_lookup_of(call_name: str, type_name: str, prefix="", postfix="") -> str:
    return f"""\
if (
    "{call_name}" == {INPUT_STR_NAME} &&
    typeid({type_name}) == {INPUT_TYPEID_NAME}
) {{
    return (void *)&{prefix}{call_name}{postfix};
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

        all_calls.append(general_load_call(subset, struct, prefix=prefix))

    return "\n\n".join(all_calls)


def generate_top_level_loader(groups: Dict[str, CallGroup]) -> str:
    all_structs = sorted(set(group.struct for group in groups.values()))

    return f"""
void *do_real_call_lookup(const std::string &name) {{
return do_lookup_trigger(name, (T **)nullptr);}}"""
