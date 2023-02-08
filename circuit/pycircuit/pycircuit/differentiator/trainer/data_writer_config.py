from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin
from typing import List, Set

from pycircuit.circuit_builder.component import ComponentOutput


@dataclass
class WriterConfig(DataClassJsonMixin):
    outputs: List[ComponentOutput]
    target_output: ComponentOutput
    sample_on: ComponentOutput
    ms_future: int
