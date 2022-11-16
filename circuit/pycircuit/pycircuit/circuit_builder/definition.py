from dataclasses import dataclass
from typing import Dict, Set

from dataclasses_json import DataClassJsonMixin


@dataclass
class OutputSpec(DataClassJsonMixin):
    fields: Set[str]


@dataclass
class Definition(DataClassJsonMixin):
    inputs: Dict[str, int]
    output: OutputSpec
    class_name: str
    static_call: bool
    ephemeral: bool

    def validate_inputs_indices(self):
        all_idxs = set(self.inputs.values())

        expected = set(range(0, len(all_idxs)))

        missing = expected - all_idxs

        assert len(missing) == 0, f"Missing indices {missing}"


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
