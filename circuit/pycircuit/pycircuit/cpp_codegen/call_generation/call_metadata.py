from dataclasses import dataclass
from typing import Set


@dataclass
class CallMetaData:
    own_self_name: str
    triggered: Set[str]
    call_name: str
