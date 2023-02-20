from dataclasses import dataclass
from typing import Dict, Set, Tuple

from dataclasses_json import DataClassJsonMixin


@dataclass
class MinutelySampleConfig(DataClassJsonMixin):
    markets: Dict[str, Set[str]]
