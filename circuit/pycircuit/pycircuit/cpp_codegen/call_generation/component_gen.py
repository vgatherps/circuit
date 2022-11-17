from abc import ABC
from dataclasses import dataclass


@dataclass
class ComponentGenMetadata:
    ephemeral_line: str
    output_line: str
