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
    written_set: frozenset[str]
    observes: frozenset[str]
    callback: Optional[str]
    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )
    outputs: frozenset[str] = frozenset()

    @property
    def skippable(self):
        return self.callback is None

    def inputs(self) -> Set[str]:
        return set(self.written_set | self.observes)


@dataclass(eq=True, frozen=True)
class OutputSpec(DataClassJsonMixin):
    ephemeral: bool
    type_path: str
    always_valid: bool = False


@dataclass(eq=True, frozen=True)
class InitSpec(DataClassJsonMixin):
    init_call: str
    metadata: frozenset[Metadata] = field(
        default_factory=frozenset, metadata=config(decoder=decode_metadata)
    )
    takes_params: bool = False


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):
    inputs: frozenset[str]
    output_specs: frozendict[str, OutputSpec]
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
