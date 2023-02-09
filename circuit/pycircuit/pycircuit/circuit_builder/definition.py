from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import dataclasses
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

from dataclasses_json import DataClassJsonMixin, config
from frozenlist import FrozenList
from frozendict import frozendict


@dataclass(eq=True, frozen=True)
class InputMetadata:
    always_valid: bool = False
    allow_unused: bool = False
    optional: bool = False


# don't really need this but makes refactoring easier
class InputMetadataMixin(ABC):
    @abstractmethod
    def input_meta(self) -> InputMetadata:
        pass

    @property
    def always_valid(self) -> bool:
        return self.input_meta().always_valid

    @property
    def optional(self) -> bool:
        return self.input_meta().optional


@dataclass(eq=True, frozen=True)
class BasicInput(InputMetadataMixin):
    meta: InputMetadata = InputMetadata()

    def input_meta(self) -> InputMetadata:
        return self.meta


@dataclass(eq=True, frozen=True)
class ArrayInput(InputMetadataMixin):
    fields: frozenset[str]
    meta: InputMetadata = InputMetadata()

    def input_meta(self) -> InputMetadata:
        return self.meta

    def get_fields_or(self, name: str):
        return self.fields or frozenset([name])


InputType = BasicInput | ArrayInput

# Test this more - python pattern matching has some weird behavior with dict overrides
def decode_input(input: Any) -> InputType:

    always_valid = bool(input.pop("always_valid", False))
    optional = bool(input.pop("optional", False))
    allow_unused = bool(input.pop("allow_unused", False))

    meta = InputMetadata(
        always_valid=always_valid, optional=optional, allow_unused=allow_unused
    )

    match input:
        case {"input_type": "single", **kwargs} | {**kwargs} if not kwargs:
            return BasicInput(meta=meta)

        case {"input_type": "array", **rest} if not rest:
            return ArrayInput(fields=frozendict(), meta=meta)
        case {"input_type": "array", "fields": [*fields], **rest} if not rest:
            for field in fields:
                if not isinstance(field, str):
                    raise ValueError(f"Field  {field} in input is not a string")
            return ArrayInput(fields=frozenset(fields), meta=meta)

        case {"input_type": "mapping", "fields": [*fields], **rest} if not rest:
            raise ValueError("Mapping inputs not supported yet")

    raise ValueError(f"Input specification did not match known input types: {input}")


def encode_input(input: InputType) -> Dict[str, Any]:
    meta_dict = input.meta.__dict__.copy()
    match input:
        case BasicInput():
            input_type = "single"
        case ArrayInput(fields=fields):
            input_type = "array"
            meta_dict["fields"] = fields
        case _:
            raise ValueError("Wrong input type passed")

    meta_dict["input_type"] = input_type
    return meta_dict


T = TypeVar("T")


def encode_dict_with(
    encoder: Callable[[T], Dict[str, Any]]
) -> Callable[[Dict[str, T]], Dict[str, Any]]:
    def do_encode(vals: Dict[str, T]) -> Dict[str, Any]:
        return {name: encoder(val) for (name, val) in vals.items()}

    return do_encode


def decode_dict_with(
    decoder: Callable[[Any], T]
) -> Callable[[Dict[str, Any]], frozendict[str, T]]:
    def do_decode(vals: Dict[str, Any]) -> Dict[str, Any]:
        return frozendict({name: decoder(val) for (name, val) in vals.items()})

    return do_decode


class Metadata(Enum):
    Timer = "timer"
    Time = "time"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


def decode_metadata(metas: List[Any]) -> frozenset[Metadata]:
    meta_lookup = {value.value: value for value in Metadata}

    meta_set = set()
    for v in metas:
        if not isinstance(v, str):
            raise ValueError("Was given non-string for metadata conversion")

        if v not in meta_lookup:
            raise ValueError(f"{v} is not a valid metadata request type")

        meta_set.add(meta_lookup[v])

    return frozenset(meta_set)


def decode_call_list(inputs: Any) -> None | str | FrozenList[str]:
    match inputs:
        case None:
            return None
        case str():
            return inputs
        case [*_]:
            raise ValueError(
                "Multiple calls per callset currently disabled at definition layer, "
                "but supported in rest of code"
            )
        case _:
            raise ValueError(f"Could not parse callback list {inputs}")


def frozen() -> FrozenList[T]:
    l: FrozenList = FrozenList()
    l.freeze()
    return l


def decode_list_with(
    decoder: Callable[[Any], T]
) -> Callable[[List[Any]], FrozenList[T]]:
    def do_decode(vals: List[Any]) -> FrozenList[Any]:
        l = FrozenList([decoder(val) for val in vals])
        l.freeze()
        return l

    return do_decode


@dataclass(eq=True, frozen=True)
class InputBatch:
    names: frozenset[str] = frozenset()


@dataclass(eq=True, frozen=True)
class CallSpec(DataClassJsonMixin):
    """A class describing a single call for a signal:

    Attributes:
        written_set: The set of inputs that must be written
                     for this component to be called

        observes: Inputs that will be passed to the signal (and ordered with),
                  but will not force triggering

        callback: The actual function to call. If it's null the signal isn't called
                   nullability probably made more sense in a callspecless-world

        metadata: Extra metadata about the environment to pass in. For example,
                  you can pass in a handle to schedule timer events on
                  the component.

        outputs: The set of outputs that are written to / triggered by the component

        cleanup: The function to call when cleaning up after the callset

        input_struct_path: Prexisting struct in the class to use for inputs

        output_struct_path: Prexisting struct in the class to use for outputs

        name: An optional name for the callset for use in ordering and disambiguation
    """

    written_set: frozenset[str]

    callback: str | List[str] | None = field(
        default=None, metadata=config(decoder=decode_call_list)
    )
    cleanup: str | List[str] | None = field(
        default=None, metadata=config(decoder=decode_call_list)
    )

    observes: frozenset[str] = frozenset()

    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )

    outputs: frozenset[str] = frozenset()

    input_struct_path: Optional[str] = None
    output_struct_path: Optional[str] = None

    name: Optional[str] = None

    @property
    def skippable(self):
        """Returns whether the callback can be skipped"""
        return self.calls() is None

    def inputs(self) -> Set[str]:
        "Convenience function to get the whole list of inputs"
        return set(self.written_set | self.observes)

    def as_cleanup(self) -> "CallSpec":
        if self.cleanup is None:
            raise ValueError("as_cleanup called on callspec with no cleanup")
        else:
            return dataclasses.replace(self, callback=self.cleanup)

    def calls(self) -> Optional[List[str]]:
        match self.callback:
            case None:
                return None
            case str():
                return [self.callback]
            case FrozenList():
                return self.callback
        raise TypeError("Bad callbacks")


@dataclass(eq=True, frozen=True)
class OutputSpec(DataClassJsonMixin):
    """Class containing information about a single given output.

    Attributes:

        ephemeral: Whether or not the output state must be stored across calls.
                   Pycircuit makes no guarantees about whether the value will be reset or not
                   if it's ephemeral, it's purely used as a possible optimization.

        type_path: Field of the parent class that describes the type

        always_valid: Whether the output can always be considered valid. This implies
                      that the components will not be able to set validity,
                      and as an optimization, pycircuit can statically mark as valid

        assume_invalid: Whether the output can be assumed invalid at the start of each
                        call. This saves storage in validity space, in addition to impacting
                        correctness for edge-triggered outputs. If an output is ephemeral
                        and can always be assumed invalid, it will be default-constructed
                        as an invalid variable in trees where it is not written.

        assume_default: Forcibly specifies that said input contains the default value
                        if it has not been written to
    """

    type_path: str
    ephemeral: bool = False
    always_valid: bool = False
    assume_invalid: bool = False
    assume_default: bool = False
    default_constructor: Optional[str] = None

    # TODO proper forcibly edge-triggered component
    # make an input that you can only reference when it's actualy triggered?

    # TODO should we do this for normal struct generation as well?
    def get_ctor(self) -> str:
        if self.default_constructor is not None:
            return self.default_constructor
        else:
            return "{}"


@dataclass(eq=True, frozen=True)
class InitSpec(DataClassJsonMixin):
    """Specifies how a component should be initialized (if at all)

    Attributes:

        init_call: The function to call for initialization

        metadata: List of metadatas to be passed to initialization

        takes_params: Whether or not json parameters should be passed in
    """

    init_call: str
    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )
    takes_params: bool = False


@dataclass(eq=True, frozen=True)
class CallsetGroup(DataClassJsonMixin):
    callsets: FrozenList[str] = field(
        default_factory=frozen, metadata=config(decoder=decode_list_with(str))
    )

    def names(self) -> frozenset[str]:
        return frozenset(set(self.callsets))


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):
    """Specifies all information about a single component

    Attributes:

        inputs: List of all input names

        output_specs: Dictionary of all outputs with their specifications

        class_name: Name of the component class

        header: Header file that must be included to get class definition

        callsets: A list of the possible triggers (aka callsets) for the component

        generic_callset: Callset to be called if there's no matching callset in a trigger

        timer_callset: Callset to be called by the timer queue

        generics_order: Order of generics to be given to class template
                        from each input. For example, the add call takes two generics
                        for each input (a and b). It would have generics order
                        {'a': 0, 'b': 1}, and the class definition would be
                        AddClass<a_type, b_type> instead of AddClass

        static_call: Whether or not the class should be called statically or on an object.
                     Classes that are called statically *will not* have a component object
                     stored in the circuit.

        init_spec: If the component requires nontrivial initialization, this specifies
                   how said initialization should be carried out.
                   This is distinct from static call - a component that simply writes a constant
                   into a circuit output would get called at init, but never get
                   called by the circuit and shouldn't ever use up any storage

        differentiable_operator_name: If the component can be replicated offline by a
                                      pytorch/tensorflow operation, this is the name of said
                                      operation.
    """

    class_name: str

    header: str

    output_specs: frozendict[str, OutputSpec] = frozenset()

    inputs: frozendict[str, InputType] = field(
        default_factory=frozendict,
        metadata=(
            config(
                decoder=decode_dict_with(decode_input),
                encoder=encode_dict_with(encode_input),
            )
        ),
    )

    callsets: frozenset[CallSpec] = frozenset()

    generic_callset: Optional[CallSpec] = None

    timer_callset: Optional[CallSpec] = None

    # On a call, we take the list of written inputs and see if they match against

    # Unused for now, but would allow components to send messages to each other
    # mailbox: frozendict[str, PingInfo] = {}

    # Defines what order generic types must be specified, if at all
    generics_order: frozendict[str, int] = field(
        default_factory=frozendict,
    )

    static_call: bool = False

    init_spec: Optional[InitSpec] = None

    default_output: Optional[str] = None

    class_generics: frozendict[str, int] = field(default_factory=frozendict)

    callset_groups: frozenset[CallsetGroup] = frozenset()

    differentiable_operator_name: Optional[str] = None

    metadata: frozendict[str, Any] = field(default_factory=frozendict)

    def validate_generics(self):
        for key in self.generics_order:
            assert key in self.all_inputs(), "Generic input is not real input"

        assert len(set(self.generics_order)) == len(
            self.generics_order
        ), "Duplicate generic inputs"

    def validate_a_callset(self, callset: CallSpec):
        if callset.skippable and callset.outputs:
            raise ValueError(
                f"A callset if both skippable but has outputs {callset.outputs} for {self.class_name}"
            )

        for written in callset.written_set:
            if written not in self.all_inputs():
                raise ValueError(
                    f"Written input {written} in {self.class_name} is not an input"
                )

            # This is reflexive so don't need to redo the check in the observes loop
            if written in callset.observes:
                raise ValueError(
                    f"Written observable {written} also an observable {self.class_name} is also observable"
                )

        for observed in callset.observes:
            if observed not in self.all_inputs():
                raise ValueError(
                    f"Observable {observed} in {self.class_name} is not an input"
                )

            if not isinstance(self.inputs[observed], BasicInput):
                raise ValueError(
                    f"A callset observes an input {observed} which is not a simple input"
                )

        if callset.callback is None and len(callset.outputs) > 0:
            raise ValueError("A non-triggering callback has outputs listed")

        aggregate_inputs = {
            input
            for input in callset.inputs()
            if not isinstance(self.inputs[input], BasicInput)
        }

        match list(aggregate_inputs):
            case []:
                pass

            case [_] if callset.cleanup is not None:
                # TODO can loosen to only explode on aggregate inputs that result
                # in multiple calls, when single-call aggregates are supported
                raise ValueError(
                    f"A call set has aggregate inputs {aggregate_inputs} but has a cleanup {callset.cleanup}"
                )

            case [_]:
                pass

            case [*_]:
                raise ValueError(
                    f"A callset is triggered on multiple aggregate inputs {aggregate_inputs}, "
                    "more than one is ill defined"
                )

    def validate_callsets(self):
        for callset in self.all_callsets():
            self.validate_a_callset(callset)

        all_used_inputs = set(
            input for callset in self.all_callsets() for input in callset.inputs()
        )

        all_my_inputs = set(self.inputs.keys())

        seen_names = set()

        for callset in self.callsets:
            if callset.name is None:
                continue
            if callset.name in seen_names:
                raise ValueError(
                    f"Definition {self.class_name} repeats callset name {callset.name}"
                )
            seen_names.add(callset.name)

        # We know that every used input is in all_inputs from the validation
        # So we can just check for equality to ensure nothing is lost
        unused_inputs = all_my_inputs.difference(all_used_inputs)
        unused_inputs = {
            unused
            for unused in unused_inputs
            if not self.inputs[unused].meta.allow_unused
        }
        if unused_inputs:
            raise ValueError(
                f"Definition {self.class_name} has unused inputs " f"{unused_inputs}"
            )

        if self.generic_callset is not None:
            if self.generic_callset.observes:
                raise ValueError(
                    f"Signal {self.class_name} has a generic callset with a nonempty observes "
                    "- all inputs must be assumed written"
                )

    def validate_callset_groups(self):
        seen_name_sets = set()
        for group in self.callset_groups:
            names = group.names()
            for name in names:
                if name not in self.callset_names():
                    raise ValueError(
                        f"Definitions {self.class_name} has callset name {name} "
                        "in a group that does not correspond to a callset"
                    )

            if names in seen_name_sets:
                raise ValueError(
                    f"Definitions {self.class_name} has callset groups "
                    f"with a duplicate set of callsets {names}"
                )
            seen_name_sets.add(names)

    def validate_timer(self):
        if self.timer_callset is not None:
            if self.timer_callset.skippable:
                raise ValueError(
                    f"Signal {self.class_name} has a skippable timer callback"
                )
            if self.timer_callset.written_set:
                raise ValueError(
                    f"Signal {self.class_name} has a timer with a nonempty written set "
                    "- all inputs must be observables"
                )
            self.validate_a_callset(self.timer_callset)

    def validate_outputs(self):
        for (output, output_spec) in self.d_output_specs.items():
            if output_spec.always_valid and output_spec.assume_invalid:
                raise ValueError(
                    f"Output {output} of {self.class_name} "
                    "is both always_valid and assumed to be invalid"
                )

            if output_spec.assume_default and not (
                output_spec.always_valid or output_spec.assume_invalid
            ):
                raise ValueError(
                    f"Output {output} of {self.class_name} "
                    "is both assumed to be default and is not always valid / assumed invalid"
                )

            if output_spec.assume_default and not output_spec.ephemeral:
                raise ValueError(
                    f"Output {output} of {self.class_name} "
                    "is both assumed to be default and is not ephemeral"
                )

            if output_spec.default_constructor and not output_spec.assume_default:
                raise ValueError(
                    f"Output {output} of {self.class_name} has a "
                    "default constructor but is not assumed to be default"
                )

        if self.default_output and self.default_output not in self.output_specs:
            raise ValueError(
                f"Definition for {self.class_name} has default output "
                f"{self.default_output} that is not in outputs"
            )

    def validate(self) -> "Definition":
        self.validate_generics()
        self.validate_callsets()
        self.validate_callset_groups()
        self.validate_outputs()
        self.validate_timer()
        return self

    def outputs(self) -> List[str]:
        return list(self.output_specs.keys())

    def all_inputs(self) -> Set[str]:
        return set(self.inputs.keys())

    def triggering_inputs(self) -> Set[str]:
        triggering = set()

        for callset in self.callsets:
            triggering |= set(callset.written_set)

        if self.generic_callset is not None:
            triggering |= set(self.generic_callset.written_set)

        if self.timer_callset is not None:
            triggering |= set(self.timer_callset.written_set)

        return triggering

    def callset_names(self) -> set[str]:
        return set(
            callset.name for callset in self.callsets if callset.name is not None
        )

    def all_callsets(self) -> Set[CallSpec]:
        return {
            callset
            for callset in list(self.callsets)
            + [self.generic_callset, self.timer_callset]
            if callset is not None
        }

    @property
    def d_output_specs(self) -> Dict[str, OutputSpec]:
        return self.output_specs

    @property
    def differentiable(self) -> bool:
        return self.differentiable_operator_name is not None


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
