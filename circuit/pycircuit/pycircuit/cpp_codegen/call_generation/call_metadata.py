from dataclasses import dataclass
from typing import Set


@dataclass
class CallMetaData:
    triggered: Set[str]
    call_name: str
