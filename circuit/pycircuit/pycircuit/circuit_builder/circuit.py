from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Set, Tuple

from dataclasses_json import DataClassJsonMixin
from pycircuit.circuit_builder.definition import Definition

# Validations:
#
# All outputs are nonaliasing - this allows us to make all pointers restrict.
# Maybe / maybe not matters? But will definitely prevent a TON of shenanigans

# Validate topologically ordered. This itself prevents


@dataclass(frozen=True, eq=True)
class ComponentOutput(DataClassJsonMixin):
    parent: str
    output: str


@dataclass
class ComponentInput(DataClassJsonMixin):
    parent: str
    output_name: str
    input_name: str
    input_idx: int

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent=self.parent, output=self.output_name)


@dataclass
class ExternalInput(DataClassJsonMixin):
    type: str
    name: str
    index: int

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent="external", output=self.name)


@dataclass
class Component:
    inputs: Dict[str, ComponentInput]
    definition: Definition
    name: str
    force_stored: bool
    index: int

    def output(self, which=None) -> ComponentOutput:
        if which is None:
            n_outputs = len(self.definition.output.fields)
            if n_outputs == 1:
                which = iter(self.definition.output.fields).__next__()
            else:
                raise ValueError(
                    f"Cannot take default output of component with {n_outputs}"
                )

        if which not in self.definition.output.fields:
            raise ValueError(f"Component {self.name} does not have field {which}")
        return ComponentOutput(
            parent=self.name,
            output=which,
        )


@dataclass
class _PartialComponent:
    inputs: Dict[str, ComponentInput]
    name: str
    definition: str
    force_stored: bool
    index: int


@dataclass
class CallGroup(DataClassJsonMixin):
    inputs: Set[str]


@dataclass
class _PartialJsonCircuit(DataClassJsonMixin):
    externals: Dict[str, ExternalInput]
    components: Dict[str, _PartialComponent]
    definitions: Dict[str, Definition]
    call_groups: Dict[str, CallGroup]


# TODO going to be A TON of wasted space here
@dataclass
class CircuitData:
    external_inputs: Dict[str, ExternalInput]
    components: Dict[str, Component]
    definitions: Dict[str, Definition]
    call_groups: Dict[str, CallGroup]

    @staticmethod
    def from_dict(the_json: Dict[str, Any]) -> "CircuitData":

        partial = _PartialJsonCircuit.from_dict(the_json)

        return CircuitData(
            external_inputs=partial.externals,
            definitions=partial.definitions,
            components={
                comp_name: Component(
                    inputs=comp.inputs,
                    name=comp.name,
                    definition=partial.definitions[comp.definition],
                    force_stored=comp.force_stored,
                    index=comp.index,
                )
                for (comp_name, comp) in partial.components.items()
            },
            call_groups=partial.call_groups,
        )

    def to_dict(self) -> Dict[str, Any]:
        def_to_name = {
            defin: defin_name for (defin_name, defin) in self.definitions.items()
        }
        partial = _PartialJsonCircuit(
            definitions=self.definitions,
            externals=self.external_inputs,
            call_groups=self.call_groups,
            components={
                comp_name: _PartialComponent(
                    name=comp.name,
                    inputs=comp.inputs,
                    definition=def_to_name[comp.definition],
                    force_stored=comp.force_stored,
                    index=comp.index,
                )
                for (comp_name, comp) in self.components.items()
            },
        )

        return partial.to_dict()


class CircuitBuilder(CircuitData):
    def __init__(self, definitions: Dict[str, Definition]):
        super().__init__(
            external_inputs={},
            components=OrderedDict(),
            definitions=definitions,
            call_groups={},
        )
        self.running_index = 0
        self.running_external = 0

    def get_external(self, name: str, type: str) -> ExternalInput:
        if name in self.external_inputs:
            return self.external_inputs[name]
        ext = ExternalInput(type=type, name=name, index=self.running_external)
        self.running_external += 1
        self.external_inputs[name] = ext
        return ext

    def add_call_group(self, name: str, group: CallGroup):
        if name in self.call_groups:
            raise ValueError(f"Circuit builder already has call group {name}")
        for ext in group.inputs:
            if ext not in self.external_inputs:
                raise ValueError(f"Call group {name} looks for missing input {ext}")
        self.call_groups[name] = group

    def make_component(
        self,
        definition_name: str,
        name: str,
        inputs: Dict[str, ComponentOutput],
        force_stored: bool = False,
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

        comp = Component(
            inputs=converted,
            definition=definition,
            name=name,
            force_stored=force_stored,
            index=self.running_index,
        )
        self.components[name] = comp
        self.running_index += 1
        return comp
