from dataclasses import dataclass, field
from typing import List, Optional, Set

from pycircuit.circuit_builder.component import ComponentOutput

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
    outputs: Set[ComponentOutput] = field(default_factory=set)
    local_prefix: str = ""
    call_params: List[str] = field(
        default_factory=list,
    )
    local_postfix: str = ""
    static_return_type: Optional[ReturnValue] = None


@dataclass
class CallGen:
    call_datas: List[CallData]
    call_path: str
