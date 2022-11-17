from abc import ABC
from dataclasses import dataclass


# TODO at some point, we'll want to split
# validity management between ephemeral components,
# and non-ephemeral components.
# this requires splitting the ephemerality checking into
# two parts. We're pretty close IMO
@dataclass
class ComponentGenMetadata:
    ephemeral_line: str
    output_line: str
