from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from dataclasses_json import DataClassJsonMixin, config
from frozendict import frozendict


def decode_frozen(json: Dict[str, Any]) -> frozendict:
    the_dict = {key: int(val) for (key, val) in json.items()}
    return frozendict(the_dict)


@dataclass(eq=True, frozen=True)
class PingInfo(DataClassJsonMixin):
    ping_with_type: str
    callback: str


@dataclass(eq=True, frozen=True)
class OutputSpec(DataClassJsonMixin):
    fields: frozenset[str]


@dataclass(eq=True, frozen=True)
class CallSpec(DataClassJsonMixin):
    written_set: frozenset[str]
    observes: frozenset[str]
    callback: str


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):
    inputs: frozenset[str]
    output: OutputSpec
    class_name: str
    static_call: bool
    ephemeral: bool
    header: str

    timer_callback: Optional[PingInfo] = None

    # This call is triggered if the written input set does not match
    # any specific triggerset
    generic_callback: Optional[str] = None

    callsets: frozenset[CallSpec] = frozenset()

    # On a call, we take the list of written inputs and see if they match against

    # Unused for now, but would allow components to send messages to each other
    # mailbox: frozendict[str, PingInfo] = {}

    # Defines what order generic types must be specified, if at all
    generics_order: frozendict[str] = field(
        default_factory=dict, metadata=config(decoder=decode_frozen)
    )

    def validate_inputs_indices(self):
        all_idxs = set(self.inputs.values())

        expected = set(range(0, len(all_idxs)))

        missing = expected - all_idxs

        assert len(missing) == 0, f"Missing indices {missing}"

    def validate_generics(self):
        for key in self.generics_order:
            assert key in self.inputs, "Generic input is not real input"

        assert len(set(self.generics_order)) == len(
            self.generics_order
        ), "Duplicate generic inputs"

    def validate_callsets(self):
        for callset in self.callsets:
            for written in callset.written_set:
                if written not in self.inputs:
                    raise ValueError(
                        f"Written observable {written} in {self.class_name} is not an input"
                    )
            for observed in callset.observes:
                if observed not in self.inputs:
                    raise ValueError(
                        f"Observable {observed} in {self.class_name} is not an input"
                    )

    def validate(self):
        self.validate_inputs_indices()
        self.validate_generics()
        self.validate_callsets()


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
