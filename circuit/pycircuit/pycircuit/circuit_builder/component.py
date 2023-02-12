from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
import dataclasses
from typing import Any, Dict, List, Mapping, Optional, Set, Union

from dataclasses_json import DataClassJsonMixin
from frozendict import frozendict
from frozenlist import FrozenList
from pycircuit.circuit_builder.definition import Definition, BasicInput, ArrayInput
from pycircuit.circuit_builder.definition import InputType, InputMetadata

TIME_TYPE = "std::uint64_t"

# TODO remove component running indices


class HasOutput(ABC):
    @abstractmethod
    def output(self) -> "ComponentOutput":
        pass

    def _make_math_component(
        self, other: "HasOutput", def_name: str, class_name: str
    ) -> "Component":

        from .circuit_context import CircuitContextManager
        from .signals.arithmetic import generate_binary_definition
        from .signals.running_name import get_novel_name

        context = CircuitContextManager.active_circuit()

        definition = generate_binary_definition(def_name, class_name)

        context.add_definition(def_name, definition)

        return context.make_component(
            definition_name=def_name,
            name=get_novel_name(def_name),
            inputs={"a": self, "b": other},
        )

    def __add__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "add", "AddComponent")

    def __sub__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "sub", "SubComponent")

    def __mul__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "mul", "MulComponent")

    def __truediv__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "div", "DivComponent")

    def __neg__(self) -> "Component":
        from pycircuit.circuit_builder.signals.unary_arithmetic import cneg

        return cneg(self)

    def __lt__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "lt", "LtComponent")

    def __le__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "le", "LeComponent")

    def __gt__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "gt", "GtComponent")

    def __ge__(self, other: "HasOutput") -> "Component":
        return self._make_math_component(other, "ge", "GeComponent")

    def __eq__(self, other) -> "Component":  # type: ignore
        if not issubclass(other, HasOutput):
            raise ValueError(
                "Can only compare an output for equality against another output"
            )
        return self._make_math_component(other, "eq", "eqComponent")

    def __getitem__(self, index: int) -> "Component":
        from .circuit_context import CircuitContextManager
        from .signals.index import generate_static_index_definition
        from .signals.running_name import get_novel_name

        context = CircuitContextManager.active_circuit()

        definition = generate_static_index_definition(index)

        def_name = f"static_index_{index}"

        context.add_definition(def_name, definition)

        return context.make_component(
            definition_name=def_name,
            name=get_novel_name(def_name),
            inputs={"a": self},
            generics={"N": str(index)},
        )


@dataclass(frozen=True, eq=True)
class ComponentOutput(DataClassJsonMixin, HasOutput):
    parent: str
    output_name: str

    def output(self) -> "ComponentOutput":
        return self


@dataclass
class ExternalInput(DataClassJsonMixin, HasOutput):
    type: str
    name: str
    index: int
    must_trigger: bool = False

    def output(self) -> ComponentOutput:
        return ComponentOutput(parent="external", output_name=self.name)


@dataclass(eq=True, frozen=True)
class SingleComponentInput(DataClassJsonMixin):
    input: ComponentOutput
    input_name: str

    def output(self) -> ComponentOutput:
        return self.input

    def outputs(self) -> List[ComponentOutput]:
        return [self.output()]

    def parents(self) -> Set[str]:
        return set(output.parent for output in self.outputs())


@dataclass(eq=True, frozen=True)
class InputBatch:
    inputs: frozendict[str, ComponentOutput]

    @property
    def d_inputs(self) -> Dict[str, ComponentOutput]:
        return self.inputs


@dataclass(eq=True, frozen=True)
class ArrayComponentInput(DataClassJsonMixin):
    inputs: FrozenList[InputBatch]
    input_name: str

    def outputs(self) -> List[ComponentOutput]:
        return [out for batch in self.inputs for out in batch.inputs.values()]

    def parents(self) -> Set[str]:
        return set(output.parent for output in self.outputs())

    def as_single_at(self, idx: int, field: str) -> SingleComponentInput:

        return SingleComponentInput(
            input_name=self.input_name, input=self.inputs[idx].inputs[field]
        )


ComponentInput = SingleComponentInput | ArrayComponentInput


@dataclass
class OutputOptions(DataClassJsonMixin):
    force_stored: bool = False
    block_propagation: bool = False

    def strongest_of(self, other: "OutputOptions") -> "OutputOptions":
        return OutputOptions(
            force_stored=self.force_stored or other.force_stored,
            block_propagation=self.block_propagation or other.block_propagation,
        )


@dataclass(eq=True, frozen=True)
class ComponentIndex:
    inputs: frozendict[str, ComponentInput]
    definition: Definition
    class_generics: frozendict[str, str]
    params: Optional[frozendict[str, Any]]


@dataclass
class Component(HasOutput):
    inputs: Dict[str, ComponentInput]
    output_options: Dict[str, OutputOptions]
    definition: Definition
    name: str
    class_generics: Dict[str, str]
    params: Optional[frozendict[str, Any]]

    def output(self, maybe_which: Optional[str] = None) -> ComponentOutput:
        match (maybe_which, self.definition.default_output):
            case (None, None):
                n_outputs = len(self.definition.output_specs)
                if n_outputs == 1:
                    return self.output(iter(self.definition.output_specs).__next__())
                raise ValueError(
                    f"Cannot take default output of component with {n_outputs}"
                )
            case (None, defin):
                return self.output(defin)

            case (which, _) if which is not None:
                if which not in self.definition.output_specs:
                    raise ValueError(
                        f"Component {self.name} does not have output {which}"
                    )
                return ComponentOutput(
                    parent=self.name,
                    output_name=which,
                )

        raise ValueError("Unreachable")

    def options(self, maybe_which: Optional[str] = None) -> OutputOptions:
        output_name = self.output(maybe_which=maybe_which).output_name

        return self.output_options.get(output_name, OutputOptions())

    def validate(self, _circuit: Any):

        from pycircuit.circuit_builder.circuit import CircuitData

        circuit: CircuitData = _circuit

        must_trigger = circuit._must_trigger_outputs()

        self.definition.validate()

        for (generic_name, generic_value) in self.class_generics.items():
            if generic_name not in self.definition.class_generics:
                raise ValueError(
                    f"Componennt {self.name} has generic {generic_name} = {generic_value} "
                    "which is not in the definition"
                )

        for generic_name in self.definition.class_generics.keys():
            if generic_name not in self.class_generics:
                raise ValueError(
                    f"Componennt {self.name} missing generic {generic_name}"
                )

        for (output_name, output_options) in self.output_options.items():
            if output_name not in self.definition.output_specs:
                raise ValueError(
                    f"Component {self.name} has output options for {output_name} which is not an output"
                )

            # TODO maybe we preserve this with the same mechanism cantor did
            # allow a callback to be done intra-invalidate?
            # feels dodgy, like this one better. almost always the right thing
            if output_options.force_stored:
                # Could let this pass if the output happens to not be ephemeral, but imo
                # that's asking for magic troubles down the line
                if self.definition.d_output_specs[output_name].assume_invalid:
                    raise ValueError(
                        f"Component {self.name} requested output {output_name} be stored, despite being assumed_invalid"
                    )

        for (input_name, comp_input) in self.inputs.items():
            # this really only possible via api misuse, no point in real exception
            assert input_name == comp_input.input_name

            if input_name not in self.definition.inputs:
                raise ValueError(
                    f"Component {self.name} has input {input_name} which is not in definitions"
                )

            validate_component_input(
                comp_input,
                self.definition.inputs[input_name],
                input_name,
                self.name,
                circuit,
            )

            all_callsets = list(self.definition.callsets) + [
                self.definition.timer_callset,
                self.definition.generic_callset,
            ]

            for callset in all_callsets:
                if callset is None:
                    continue
                # It doesn't evenmake sense to observe an array input - need to banish
                for observed in callset.observes:
                    for output in self.inputs[observed].outputs():
                        if output in must_trigger:
                            raise ValueError(
                                f"Component {self.name} has input {observed} which links to an output "
                                "that requires triggering, and is not triggered"
                            )

        for (input_name, input) in self.definition.inputs.items():
            if input_name not in self.inputs and not input.optional:
                raise ValueError(f"Component {self.name} is missing input {input_name}")

    def triggering_inputs(self) -> List[ComponentInput]:
        return [self.inputs[inp] for inp in self.definition.triggering_inputs()]

    def force_stored(self, output: str | None = None):
        real_output = self.output(output)

        if real_output.output_name not in self.output_options:
            self.output_options[real_output.output_name] = OutputOptions(
                force_stored=True
            )
        else:
            self.output_options[real_output.output_name] = dataclasses.replace(
                self.output_options[real_output.output_name], force_stored=True
            )

    def block_propagation(self, output: str | None = None):
        real_output = self.output(output)
        if real_output.output_name not in self.output_options:
            self.output_options[real_output.output_name] = OutputOptions(
                block_propagation=True
            )
        else:
            self.output_options[real_output.output_name] = dataclasses.replace(
                self.output_options[real_output.output_name], block_propagation=True
            )

    def index(self) -> ComponentIndex:
        return ComponentIndex(
            inputs=frozendict(self.inputs),
            definition=self.definition,
            class_generics=frozendict(self.class_generics),
            params=self.params,
        )


def validate_component_input(
    comp_input: ComponentInput,
    def_input: InputType,
    input_name: str,
    component_name: str,
    _circuit,
):

    from pycircuit.circuit_builder.circuit import CircuitData

    circuit: CircuitData = _circuit

    seen_outputs = set()
    for output in comp_input.outputs():
        if output in seen_outputs:
            raise ValueError(
                f"Input {input_name} of component {component_name} "
                f"saw output {output} duplicate times"
            )
        seen_outputs.add(output)

    always_valid = def_input.always_valid

    match (comp_input, def_input):
        case (SingleComponentInput(), BasicInput()):
            pass

        case (
            ArrayComponentInput(inputs=arr_inputs),
            ArrayInput() as def_input,
        ):
            arr_fields = def_input.get_fields_or(input_name)
            for (arr_idx, arr_input) in enumerate(arr_inputs):
                input_keys = frozenset(arr_input.inputs.keys())
                if input_keys != arr_fields:
                    raise ValueError(
                        f"Input batch at idx {arr_idx} of input {input_name} "
                        f"for component {component_name} had fields {input_keys} "
                        f"but expected {arr_fields}"
                    )
        case _:
            raise ValueError(
                f"Input of type {type(comp_input)} was given but expected {type(def_input)}"
            )

    for output in comp_input.outputs():
        match (always_valid, output.parent):
            case (True, "external"):
                raise ValueError(
                    f"Input {input_name} of component {component_name} "
                    f"must always be valid but references an external output "
                    f"{output.output_name}"
                    "which is not always valid"
                )
            case (True, parent):
                parent_comp = circuit.components[parent]
                parent_valid = parent_comp.definition.d_output_specs[
                    output.output_name
                ].always_valid
                if always_valid and not parent_valid:
                    raise ValueError(
                        f"Input {input_name} of component {component_name} "
                        f"must always be valid but references a output "
                        f"{output.output_name} of component {output.parent} "
                        "which is not always valid"
                    )
            case _:
                pass
