from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataclasses_json import DataClassJsonMixin
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
    ephemeral: bool
    type_path: str


@dataclass(eq=True, frozen=True)
class CallSpec(DataClassJsonMixin):
    written_set: frozenset[str]
    observes: frozenset[str]
    callback: Optional[str]
    outputs: frozenset[str] = frozenset()

    @property
    def skippable(self):
        return self.callback is None


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):
    inputs: frozenset[str]
    outputs: frozendict[str, OutputSpec]
    class_name: str

    # TODO should static call actually be a feature of the writeset?
    # personally feel like no
    static_call: bool

    header: str

    timer_callback: Optional[PingInfo] = None

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

    def validate_generics(self):
        for key in self.generics_order:
            assert key in self.inputs, "Generic input is not real input"

        assert len(set(self.generics_order)) == len(
            self.generics_order
        ), "Duplicate generic inputs"

    def validate_callsets(self):
        for callset in self.callsets:
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

    def validate(self):
        self.validate_generics()
        self.validate_callsets()

    def all_outputs(self) -> List[str]:
        return list(self.outputs.keys())

    @property
    def d_outputs(self) -> Dict[str, OutputSpec]:
        return self.outputs


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
