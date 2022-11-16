from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Set, Tuple

from pycircuit.circuit_builder.definition import Definition

# Validations:
#
# All outputs are nonaliasing - this allows us to make all pointers restrict.
# Maybe / maybe not matters? But will definitely prevent a TON of shenanigans

# Validate topologically ordered. This itself prevents


@dataclass(frozen=True, eq=True)
class ComponentOutput:
    parent: str
    output: str


@dataclass
class ComponentInput:
    parent: str
    output_name: str
    input_name: str
    input_idx: int

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent=self.parent, output=self.output_name)


@dataclass
class ExternalInput:
    type: str
    name: str

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent="external", output=self.name)


@dataclass
class CallGroups:
    inputs: Set[str]


class Circuit:
    def __init__(self, definitions: Dict[str, Definition]):
        self.definitions = definitions
        self.components: OrderedDict[str, "Component"] = OrderedDict()
        self.external_inputs: Dict[str, ExternalInput] = {}

    def get_external(self, name: str, type: str) -> ExternalInput:
        if name in self.external_inputs:
            return self.external_inputs[name]
        ext = ExternalInput(type=type, name=name)
        self.external_inputs[name] = ext
        return ext

    def make_component(
        self, definition_name: str, name: str, inputs: Dict[str, ComponentOutput]
    ) -> "Component":
        assert name not in self.components

        definition = self.definitions[definition_name]
        converted = {}

        for (in_name, input) in inputs.items():
            converted[in_name] = ComponentInput(
                parent=input.parent,
                output_name=input.output,
                input_name=in_name,
                input_idx=definition.inputs[in_name],
            )

        comp = Component(inputs=converted, definition=definition, name=name)
        self.components[name] = comp
        return comp


@dataclass
class Component:
    inputs: Dict[str, ComponentInput]
    definition: Definition
    name: str
