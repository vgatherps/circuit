from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

# TODO PERF
# I think we can do a FAR better job of annotating with restrict.
# For all validity markers, they're modified in-call,
# so we can just take references and mark restrict when needed

# For objects/externals
# probably want to take a restrict pointer to the objects class at the top
# of the scope

# For outputs:
# If not modified in the call, can just use an output block with a restrict reference
# If they are modified, am not personally that confident in restrict behaving well
# when crossing a function boundary (i.e. getting passed to an opaque signal)


@dataclass
class ReturnValue:
    name: str
    static_return_type: Optional[str] = None

    @property
    def return_type(self) -> str:
        if self.static_return_type is not None:
            return self.static_return_type
        else:
            return "auto"


@dataclass
class CallData:
    global_prefix: str = ""
    local_prefix: str = ""
    call_params: List[str] = field(
        default_factory=list,
    )
    local_postfix: str = ""
    static_return_type: Optional[ReturnValue] = None


def assemble_call_from(call_path: str, calls: Sequence[CallData]):
    calls = list(calls)

    return_type = None

    for call in calls:
        requested_type = call.static_return_type
        if requested_type is not None:
            if return_type is not None:
                raise ValueError(
                    "Multiple call data generators requested a return type"
                )

            return_type = requested_type

    global_prefix_lines = "\n".join(call.global_prefix for call in calls)
    prefix_lines = "\n".join(call.local_prefix for call in calls)
    postfix_lines = "\n".join(call.local_postfix for call in calls)

    call_params = ",".join(
        call_param for call in calls for call_param in call.call_params
    )

    full_invocation = f"{call_path}({call_params})"

    if return_type is not None:
        call_line = f"{return_type.return_type} {return_type.name} = {full_invocation};"
    else:
        call_line = f"{full_invocation};"

    return f"""
    {global_prefix_lines}
    {{
        {prefix_lines}
        {call_line}
        {postfix_lines}
    }}
"""
