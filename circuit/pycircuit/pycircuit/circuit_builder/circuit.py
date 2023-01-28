from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Set, Union

from dataclasses_json import DataClassJsonMixin
from frozendict import frozendict
from frozenlist import FrozenList

from pycircuit.circuit_builder.definition import Definition, BasicInput, ArrayInput
from pycircuit.circuit_builder.definition import InputType
from pycircuit.circuit_builder.component import Component
from pycircuit.circuit_builder.component import (
    TIME_TYPE,
    ArrayComponentInput,
    ComponentInput,
    ExternalInput,
    HasOutput,
    InputBatch,
    OutputOptions,
    SingleComponentInput,
)
from pycircuit.circuit_builder.component import ComponentOutput

from .signals.constant import generate_constant_definition


@dataclass
class _PartialComponent(DataClassJsonMixin):
    inputs: Dict[str, ComponentInput]
    output_options: Dict[str, OutputOptions]
    name: str
    definition: str
    class_generics: Dict[str, str]


@dataclass(eq=True, frozen=True)
class ExternalStruct:
    struct_name: str
    header: Optional[str] = None


@dataclass(eq=True, frozen=True)
class CallStruct(DataClassJsonMixin):
    inputs: frozendict[str, str]

    external_struct: Optional[ExternalStruct] = None

    @staticmethod
    def from_input_dict(
        inputs: Dict[str, str],
        external_struct: Optional[ExternalStruct] = None,
    ) -> "CallStruct":
        return CallStruct(inputs=frozendict(inputs), external_struct=external_struct)

    @staticmethod
    def from_inputs(
        external_struct: Optional[ExternalStruct] = None,
        **fields: str,
    ) -> "CallStruct":
        return CallStruct(inputs=frozendict(fields), external_struct=external_struct)

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


@dataclass
class OutputSingle:
    input: HasOutput


@dataclass
class OutputArray:
    inputs: List[Dict[str, HasOutput]]


InputForComponent = Union[HasOutput, OutputSingle, OutputArray]

# TODO going to be A TON of wasted space here
@dataclass
class CircuitData:
    external_inputs: Dict[str, ExternalInput]
    components: Dict[str, Component]
    definitions: Dict[str, Definition]
    call_groups: Dict[str, CallGroup]
    call_structs: Dict[str, CallStruct]

    def _must_trigger_outputs(self) -> Set[ComponentOutput]:
        return {
            ext.output() for ext in self.external_inputs.values() if ext.must_trigger
        }

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
                    class_generics=comp.class_generics,
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
                    output_options=comp.output_options,
                    class_generics=comp.class_generics,
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
        self.running_external = 0

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

    def add_call_struct_from(
        self, name: str, external_struct: Optional[ExternalStruct] = None, **fields: str
    ):
        self.add_call_struct(
            name, CallStruct.from_inputs(**fields, external_struct=external_struct)
        )

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
        inputs: Mapping[str, InputForComponent],
        output_options: Dict[str, OutputOptions] = {},
        generics: Dict[str, str] = {},
    ) -> "Component":
        assert name not in self.components

        definition = self.definitions[definition_name]
        converted: Dict[str, ComponentInput] = {}

        for (in_name, an_input) in inputs.items():
            match an_input:
                case (HasOutput() as input) | OutputSingle(input):
                    converted[in_name] = SingleComponentInput(
                        input=input.output(),
                        input_name=in_name,
                    )
                case OutputArray(inputs=arr_input):
                    fronzen_inputs = FrozenList(
                        InputBatch(
                            frozendict(
                                {
                                    batch_key: batch_val.output()
                                    for (batch_key, batch_val) in batch.items()
                                }
                            )
                        )
                        for batch in arr_input
                    )

                    fronzen_inputs.freeze()
                    converted[in_name] = ArrayComponentInput(
                        inputs=fronzen_inputs, input_name=in_name
                    )
                case _:
                    raise ValueError("")

        comp = Component(
            inputs=converted,
            definition=definition,
            output_options=output_options,
            name=name,
            class_generics=generics,
        )

        comp.validate(self)

        self.components[name] = comp
        return comp

    def make_constant(self, type: str, constructor: Optional[str]) -> "Component":
        definition = generate_constant_definition(type, constructor)
        if constructor is not None:
            ctor_name = constructor
        else:
            ctor_name = "{}"
        def_name = f"constant_{type}_{ctor_name}"

        self.add_definititon(def_name, definition)

        comp = Component(
            name=def_name,
            definition=definition,
            inputs={},
            output_options={},
            class_generics={},
        )
        if def_name in self.components:
            if self.components[def_name].definition == definition:
                return self.components[def_name]
            raise ValueError(
                f"Already have constant {def_name} but with different definition - likely a bug"
            )

        self.components[def_name] = comp

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
        for other_component in self.components.values():
            if other_component is component:
                continue
            # TODO only do for triggering inputs?
            for input in other_component.inputs.values():
                for parent in input.parents():
                    if parent == component.name:
                        raise ValueError(
                            f"Trying to rename component {component.name} to {new_name} "
                            f"but {other_component.name} already depends on it"
                        )

        del self.components[component.name]
        component.name = new_name
        self.components[new_name] = component
