from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Set

from dataclasses_json import DataClassJsonMixin
from frozendict import frozendict
from pycircuit.circuit_builder.definition import Definition

from .signals.arithmetic import generate_binary_definition
from .signals.running_name import get_novel_name

TIME_TYPE = "std::uint64_t"


class HasOutput(ABC):
    @abstractmethod
    def output(self) -> "ComponentOutput":
        pass

    def _make_math_component(
        self, other: "HasOutput", def_name: str, class_name: str
    ) -> "Component":

        from .circuit_context import CircuitContextManager

        context = CircuitContextManager.active_circuit()

        definition = generate_binary_definition(class_name)

        context.add_definititon(def_name, definition)

        # TODO output options
        return context.make_component(
            definition_name=def_name,
            name=get_novel_name(def_name),
            inputs={"a": self.output(), "b": other.output()},
        )

    def __add__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "add", "AddComponent")

    def __sub__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "sub", "SubComponent")

    def __mul__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "mul", "MulComponent")

    def __truediv__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "div", "DivComponent")


@dataclass(frozen=True, eq=True)
class ComponentOutput(DataClassJsonMixin, HasOutput):
    parent: str
    output_name: str

    def output(self) -> "ComponentOutput":
        return self


@dataclass(eq=True, frozen=True)
class ComponentInput(DataClassJsonMixin, HasOutput):
    parent: str
    output_name: str
    input_name: str

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent=self.parent, output_name=self.output_name)


@dataclass
class ExternalInput(DataClassJsonMixin, HasOutput):
    type: str
    name: str
    index: int
    must_trigger: bool = False

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent="external", output_name=self.name)


@dataclass
class OutputOptions(DataClassJsonMixin):
    force_stored: bool


@dataclass
class Component(HasOutput):
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
            output_name=which,
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


@dataclass(eq=True, frozen=True)
class CallStruct(DataClassJsonMixin):
    inputs: frozendict[str, str]

    @staticmethod
    def from_input_dict(inputs: Dict[str, str]) -> "CallStruct":
        return CallStruct(inputs=frozendict(inputs))

    @staticmethod
    def from_inputs(**fields: str) -> "CallStruct":
        return CallStruct(inputs=frozendict(fields))

    @property
    def d_inputs(self) -> Dict[str, str]:
        return self.inputs


@dataclass
class CallGroup(DataClassJsonMixin):
    struct: str
    external_field_mapping: Dict[str, str]

    @property
    def inputs(self) -> Set[str]:
        return set(self.external_field_mapping.values())


@dataclass
class _PartialJsonCircuit(DataClassJsonMixin):
    externals: Dict[str, ExternalInput]
    components: Dict[str, _PartialComponent]
    definitions: Dict[str, Definition]
    call_groups: Dict[str, CallGroup]
    call_structs: Dict[str, CallStruct]


# TODO going to be A TON of wasted space here
@dataclass
class CircuitData:
    external_inputs: Dict[str, ExternalInput]
    components: Dict[str, Component]
    definitions: Dict[str, Definition]
    call_groups: Dict[str, CallGroup]
    call_structs: Dict[str, CallStruct]

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
            call_structs=partial.call_structs,
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
            call_structs=self.call_structs,
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

    def validate_call_group(self, name: str, group: CallGroup):
        if group.struct not in self.call_structs:
            raise ValueError(
                f"Call group {name} requested nonexstent input struct {group.struct}"
            )
        struct = self.call_structs[group.struct]
        for (struct_field, external_name) in group.external_field_mapping.items():
            if struct_field not in struct.d_inputs:
                raise ValueError(
                    f"Call group {name} requested field {struct_field} from struct {group.struct} but does not exist"
                )

            if external_name not in self.external_inputs:
                raise ValueError(
                    f"Call group {name} requested external {external_name} but does not exist"
                )

            external_type = self.external_inputs[external_name].type

            field_type = struct.d_inputs[struct_field]

            if external_type != field_type:
                raise ValueError(
                    f"Call group {name} mapped field {struct_field} to external {external_name} with "
                    f"different types {field_type} and {external_type}"
                )

    def validate(self):
        for component in self.components.values():
            component.validate(self)

        for name, group in self.call_groups.items():
            self.validate_call_group(name, group)


class CircuitBuilder(CircuitData):
    def __init__(self, definitions: Dict[str, Definition]):
        super().__init__(
            external_inputs={},
            components=OrderedDict(),
            definitions=definitions,
            call_groups={},
            call_structs={},
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

    def add_call_struct(self, name: str, struct: CallStruct):
        if name in self.call_structs:
            existing = self.call_structs[name]
            if struct != existing:
                raise ValueError(
                    f"Trying to add call struct {name} {struct},"
                    f" but different one {existing} existed"
                )
        self.call_structs[name] = struct

    def add_call_struct_from(self, name: str, **fields: str):
        self.add_call_struct(name, CallStruct.from_inputs(**fields))

    def add_call_group(self, name: str, group: CallGroup):
        if name in self.call_groups:
            raise ValueError(f"Circuit builder already has call group {name}")

        self.validate_call_group(name, group)

        self.call_groups[name] = group

    def add_definititon(self, name: str, definition: Definition):
        if name in self.definitions:
            if definition != self.definitions[name]:
                raise ValueError(
                    f"Tried to add two different definitions for name {name}"
                )
        else:
            definition.validate()
            self.definitions[name] = definition

    def make_component(
        self,
        definition_name: str,
        name: str,
        inputs: Mapping[str, HasOutput],
        output_options: Dict[str, OutputOptions] = {},
    ) -> "Component":
        assert name not in self.components

        definition = self.definitions[definition_name]
        converted = {}

        for (in_name, input) in inputs.items():
            converted[in_name] = ComponentInput(
                parent=input.output().parent,
                output_name=input.output().output_name,
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

    # TODO introduce weak renaming - only rename if someone hasn't already
    # Much more useful when we start deduplicating
    def rename_component(self, component: Component, new_name: str):
        if new_name == component.name:
            return
        if component.name not in self.components:
            raise ValueError(
                f"Trying to rename component {component.name} to {new_name} that is not part of the circuit"
            )

        # TODO add reverse mapping table to speed up this step
        for component in self.components.values():
            # TODO only do for triggering inputs?
            for input in component.inputs.values():
                if input.parent == component.name:
                    raise ValueError(
                        f"Trying to rename component {component.name} to {new_name} "
                        f"but {input.parent} already depends on it"
                    )

        del self.components[component.name]
        component.name = new_name
        self.components[new_name] = component
