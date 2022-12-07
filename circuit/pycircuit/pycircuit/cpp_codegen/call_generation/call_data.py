from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence


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


class CallDataGenerator(ABC):
    def get_global_prefix_lines(self) -> str:
        return ""

    def get_prefix_lines(self) -> str:
        return ""

    def get_call_params(self) -> str:
        return ""

    def get_postfix_lines(self) -> str:
        return ""

    def give_return_type(self) -> Optional[ReturnValue]:
        return None


def assemble_call_from(calls: Sequence[CallDataGenerator]):
    calls = list(calls)

    return_type = None

    for call in calls:
        requested_type = call.give_return_type()
        if requested_type is not None:
            if return_type is not None:
                raise ValueError(
                    "Multiple call data generators requested a return type"
                )

            return_type = requested_type

    global_prefix_lines = "\n".join(call.get_global_prefix_lines() for call in calls)

    prefix_lines = "\n".join(call.get_prefix_lines() for call in calls)

    postfix_lines = "\n".join(call.get_postfix_lines() for call in calls)

    call_line = "fixme"

    if return_type is not None:
        call_line = f"{return_type.return_type} {return_type.name} = {call_line}"

    return f"""
    {global_prefix_lines}
    {{
        {prefix_lines}
        {call_line}
        {postfix_lines}
    }}
"""
