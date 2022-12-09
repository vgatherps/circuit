from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from dataclasses_json import DataClassJsonMixin, config
from frozendict import frozendict


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

    observes: frozenset[str]

    callback: Optional[str]

    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )

    outputs: frozenset[str] = frozenset()

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
    """

    ephemeral: bool
    type_path: str
    always_valid: bool = False

    # TODO invalid_unless_written
    # for something like tick - implies that it should be considered invalid
    # unless a previous component wrote it!
    # This is requires for the mix of decaying sum and tick aggregator to work
    # properly, and is a huge optimization. If the output is ephemeral,
    # this implies that the output will *never* be stored as it will provably be invalid
    # in calls where it's not written


@dataclass(eq=True, frozen=True)
class InitSpec(DataClassJsonMixin):
    init_call: str
    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )
    takes_params: bool = False


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):

    # Describes the list of valid inputs the signal can take
    inputs: frozenset[str]

    # Describes the possible outputs and details about them
    output_specs: frozendict[str, OutputSpec]

    # Class name of the calling component
    class_name: str

    header: str

    timer_callback: Optional[CallSpec] = None

    # This call is triggered if the written input set does not match
    # any specific triggerset
    generic_callset: Optional[CallSpec] = None

    callsets: frozenset[CallSpec] = frozenset()

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
            assert key in self.inputs, "Generic input is not real input"

        assert len(set(self.generics_order)) == len(
            self.generics_order
        ), "Duplicate generic inputs"

    def validate_a_callset(self, callset: CallSpec):
        if callset.skippable and callset.outputs:
            raise ValueError(
                f"A callset if both skippable but has outputs {callset.outputs} for {self.class_name}"
            )
        for written in callset.written_set:
            if written not in self.inputs:
                raise ValueError(
                    f"Written observable {written} in {self.class_name} is not an input"
                )

            # This is reflexive so don't need to redo the check in the observes loop
            if written in callset.observes:
                raise ValueError(
                    f"Written observable {written} also an observable {self.class_name} is also observable"
                )

        for observed in callset.observes:
            if observed not in self.inputs:
                raise ValueError(
                    f"Observable {observed} in {self.class_name} is not an input"
                )

    def validate_callsets(self):
        for callset in self.callsets:
            self.validate_a_callset(callset)

    def validate_timer(self):
        if self.timer_callback is not None:
            if self.timer_callback.skippable:
                raise ValueError(
                    f"Signal {self.class_name} has a skippable timer callback"
                )
            self.validate_a_callset(self.timer_callback)

    def validate(self):
        self.validate_generics()
        self.validate_callsets()
        self.validate_timer()

    def outputs(self) -> List[str]:
        return list(self.output_specs.keys())

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
