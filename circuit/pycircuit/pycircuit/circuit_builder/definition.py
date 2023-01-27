from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union

from dataclasses_json import DataClassJsonMixin, config
from frozendict import frozendict


@dataclass(eq=True, frozen=True)
class BasicInput:
    pass


@dataclass(eq=True, frozen=True)
class ArrayInput:
    per_entry: frozenset[str]


InputType = BasicInput


def decode_input(input: Any) -> InputType:
    match input:
        case {} | {'input_type': 'single'}:
            return BasicInput()
        case {'input_type': 'array', 'fields': [*fields]}:
            raise ValueError("Array inputs not supported yet")
        case {'input_type': 'mapping', 'fields': [*fields]}:
            raise ValueError("Array inputs not supported yet")
        case _:
            raise ValueError(f"Input specification did not match known input types: {input}")

def encode_input(input: InputType) -> Dict[str, Any]:
    match input:
        case BasicInput():
            return {'input_type': 'single'}
        case _:
            raise ValueError("Wrong input type passed")

T = TypeVar('T')

def encode_dict_with(encoder: Callable[[T], Dict[str, Any]]) -> Callable[[Dict[str, T]], Dict[str, Any]]:
    def do_encode(vals: Dict[str, T]) -> Dict[str, Any]:
        return {
            name: encoder(val) for (name, val) in vals.items()
        }

    return do_encode

def decode_dict_with(decoder: Callable[[Any], T]) -> Callable[[Dict[str, Any]], frozendict[str, T]]:
    def do_decode(vals: Dict[str, Any]) -> Dict[str, Any]:
        return frozendict({
            name: decoder(val) for (name, val) in vals.items()
        })

    return do_decode


class Metadata(Enum):
    Timer = "timer"

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
    """

    written_set: frozenset[str]

    callback: Optional[str]

    observes: frozenset[str] = frozenset()

    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )

    outputs: frozenset[str] = frozenset()

    input_struct_path: Optional[str] = None
    output_struct_path: Optional[str] = None

    cleanup: Optional[str] = None

    @property
    def skippable(self):
        """Returns whether the callback can be skipped"""
        return self.callback is None

    def inputs(self) -> Set[str]:
        "Convenience function to get the whole list of inputs"
        return set(self.written_set | self.observes)


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
    """

    class_name: str

    header: str

    output_specs: frozendict[str, OutputSpec] = frozenset()

    inputs: frozendict[str, InputType] = field(
        default_factory=frozenset, metadata=(config(decoder=decode_dict_with(decode_input), encoder=encode_dict_with(encode_input)))
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
                    f"Written observable {written} in {self.class_name} is not an input"
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

        if callset.callback is None and len(callset.outputs) > 0:
            raise ValueError("A non-triggering callback has outputs listed")

    def validate_callsets(self):
        for callset in self.callsets:
            self.validate_a_callset(callset)

        if self.generic_callset is not None:
            if self.generic_callset.observes:
                raise ValueError(
                    f"Signal {self.class_name} has a generic callset with a nonempty observes"
                    "- all inputs must be assumed written"
                )

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
                    f"Output {output} of {self.class_name} is both always_valid and assumed to be invalid"
                )

            if output_spec.assume_default and not output_spec.always_valid:
                raise ValueError(
                    f"Output {output} of {self.class_name} is both assumed to be default and is not always valid"
                )

            if output_spec.assume_default and not output_spec.ephemeral:
                raise ValueError(
                    f"Output {output} of {self.class_name} is both assumed to be default and is not ephemeral"
                )

            if output_spec.default_constructor and not output_spec.assume_default:
                raise ValueError(
                    f"Output {output} of {self.class_name} has a default constructor but is not assumed to be default"
                )

    def validate(self):
        self.validate_generics()
        self.validate_callsets()
        self.validate_outputs()
        self.validate_timer()

    def outputs(self) -> List[str]:
        return list(self.output_specs.keys())

    def all_inputs(self) -> Set[str]:
        return set(self.inputs.keys())

    def triggering_inputs(self) -> Set[str]:
        triggering = set()

        for callset in self.callsets:
            triggering |= set(callset.written_set)

        if self.generic_callset is not None:
            triggering |= self.generic_callset.written_set

        return triggering

    @property
    def d_output_specs(self) -> Dict[str, OutputSpec]:
        return self.output_specs


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
