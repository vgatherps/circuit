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
    must_trigger: bool = False

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

    def validate(self, circuit: "CircuitData"):

        self.definition.validate()

        for (output, output_options) in self.output_options.items():
            if output not in self.definition.output_specs:
                raise ValueError(
                    f"Component {self.name} has output options for {output} which is not an output"
                )

            # TODO maybe we preserve this with the same mechanism cantor did
            # allow a callback to be done intra-invalidate?
            # feels dodgy, like this one better. almost always the right thing
            if output_options.force_stored:
                # Could let this pass if the output happens to not be ephemeral, but imo
                # that's asking for magic troubles down the line
                if self.definition.d_output_specs[output].assume_invalid:
                    raise ValueError(
                        f"Component {self.name} requested output {output} be stored, despite being assumed_invalid"
                    )

        for (input, comp_input) in self.inputs.items():
            # this really only possible via api misuse, no point in real exception
            assert input == comp_input.input_name

            if input not in self.definition.inputs:
                raise ValueError(
                    f"Component {self.name} has input {input} which is not in definitions"
                )

            if comp_input.parent == "external":
                external = circuit.external_inputs[comp_input.output_name]

                if external.must_trigger:
                    in_callset = False
                    for callset in list(self.definition.callsets) + [
                        self.definition.timer_callset,
                        self.definition.generic_callset,
                    ]:
                        if callset:
                            in_callset |= comp_input.input_name in callset.observes

                    if in_callset:
                        raise ValueError(
                            f"Component {self.name} has input {input} which links to a an external "
                            "that requires triggering, and is not triggered"
                        )

        for input in self.definition.inputs:
            if input not in self.inputs:
                raise ValueError(f"Component {self.name} is missing input {input}")

    def triggering_inputs(self) -> List[ComponentInput]:
        return [self.inputs[inp] for inp in self.definition.triggering_inputs()]


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

        data.validate()

        return data

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
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

    def validate(self):
        for component in self.components.values():
            component.validate(self)


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

    def get_external(
        self, name: str, type: str, must_trigger: bool = False
    ) -> ExternalInput:
        if name in self.external_inputs:
            ext = self.external_inputs[name]
            candidate_external = ExternalInput(
                name=name, type=type, index=ext.index, must_trigger=must_trigger
            )
            if candidate_external != ext:
                raise ValueError(
                    f"External {name} requested at {candidate_external} but already exists as {ext}"
                )
            return ext
        ext = ExternalInput(
            type=type, name=name, index=self.running_external, must_trigger=must_trigger
        )
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
        comp.validate(self)
        return comp
