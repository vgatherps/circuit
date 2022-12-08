from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from dataclasses_json import DataClassJsonMixin
from pycircuit.circuit_builder.definition import Definition
from typing_extensions import Protocol

# Validations:
#
# All outputs are nonaliasing - this allows us to make all pointers restrict.
# Maybe / maybe not matters? But will definitely prevent a TON of shenanigans

# Validate topologically ordered. This itself prevents

TIME_TYPE = "std::uint64_t"


class HasOutput(Protocol):
    def output(self) -> "ComponentOutput":
        pass


@dataclass(frozen=True, eq=True)
class ComponentOutput(DataClassJsonMixin):
    parent: str
    output: str


@dataclass(eq=True, frozen=True)
class ComponentInput(DataClassJsonMixin):
    parent: str
    output_name: str
    input_name: str

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
class OutputOptions(DataClassJsonMixin):
    force_stored: bool


@dataclass
class Component:
    inputs: Dict[str, ComponentInput]
    output_options: Dict[str, OutputOptions]
    definition: Definition
    name: str
    index: int

    def triggering_inputs(self) -> List[ComponentInput]:
        return [
            comp_input
            for (input, comp_input) in self.inputs.items()
            if not self.definition.d_input_specs[input].non_triggering
        ]

    def output(self, which=None) -> ComponentOutput:
        if which is None:
            n_outputs = len(self.definition.output_specs)
            if n_outputs == 1:
                which = iter(self.definition.output_specs).__next__()
            else:
                raise ValueError(
                    f"Cannot take default output of component with {n_outputs}"
                )

        if which not in self.definition.output_specs:
            raise ValueError(f"Component {self.name} does not have output {which}")
        return ComponentOutput(
            parent=self.name,
            output=which,
        )

    def validate(self):

        self.definition.validate()

        for output in self.output_options:
            if output not in self.definition.output_specs:
                raise ValueError(
                    f"Component {self.name} has output options for {output} which is not an output"
                )

        for (input, comp_input) in self.inputs.items():
            # this really only possible via api misuse, no point in real exception
            assert input == comp_input.input_name

            if input not in self.definition.inputs:
                raise ValueError(
                    f"Component {self.name} has input {input} which is not in definitions"
                )

        for input in self.definition.inputs:
            if input not in self.inputs:
                raise ValueError(f"Component {self.name} is missing input {input}")


@dataclass
class _PartialComponent(DataClassJsonMixin):
    inputs: Dict[str, ComponentInput]
    output_options: Dict[str, OutputOptions]
    name: str
    definition: str
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

        for defin in partial.definitions.values():
            defin.validate()

        data = CircuitData(
            external_inputs=partial.externals,
            definitions=partial.definitions,
            components={
                comp_name: Component(
                    inputs=comp.inputs,
                    output_options=comp.output_options,
                    name=comp.name,
                    definition=partial.definitions[comp.definition],
                    index=comp.index,
                )
                for (comp_name, comp) in partial.components.items()
            },
            call_groups=partial.call_groups,
        )

        for component in data.components.values():
            component.validate()

        return data

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
                    index=comp.index,
                    output_options=comp.output_options,
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

        self.get_external("time", TIME_TYPE)

    def get_external(self, name: str, type: str) -> ExternalInput:
        if name in self.external_inputs:
            ext = self.external_inputs[type]
            if type !=ext.type:
                raise ValueError(f"External {name} requested with type {type} but already has type {ext.type}")
            return ext
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
        output_options: Dict[str, OutputOptions] = {},
    ) -> "Component":
        assert name not in self.components

        definition = self.definitions[definition_name]
        converted = {}

        for (in_name, input) in inputs.items():
            converted[in_name] = ComponentInput(
                parent=input.parent,
                output_name=input.output,
                input_name=in_name,
            )

        comp = Component(
            inputs=converted,
            definition=definition,
            output_options=output_options,
            name=name,
            index=self.running_index,
        )
        self.components[name] = comp
        self.running_index += 1
        comp.validate()
        return comp
