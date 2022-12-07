from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from dataclasses_json import DataClassJsonMixin
from frozendict import frozendict


def decode_frozen(json: Dict[str, Any]) -> frozendict:
    the_dict = {key: int(val) for (key, val) in json.items()}
    return frozendict(the_dict)


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
class PingInfo(DataClassJsonMixin):
    ping_with_type: str
    call: CallSpec


@dataclass(eq=True, frozen=True)
class InputSpec(DataClassJsonMixin):
    non_triggering: bool = False


@dataclass(eq=True, frozen=True)
class OutputSpec(DataClassJsonMixin):
    ephemeral: bool
    type_path: str
    always_valid: bool = False


@dataclass(eq=True, frozen=True)
class InitSpec(DataClassJsonMixin):
    init_call: str
    takes_params: bool = False


@dataclass(eq=True, frozen=True)
class Definition(DataClassJsonMixin):
    input_specs: frozendict[str, InputSpec]
    output_specs: frozendict[str, OutputSpec]
    class_name: str

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

    static_call: bool = False

    init_spec: Optional[InitSpec] = None

    def validate_generics(self):
        for key in self.generics_order:
            assert key in self.input_specs, "Generic input is not real input"

        assert len(set(self.generics_order)) == len(
            self.generics_order
        ), "Duplicate generic inputs"

    def validate_a_callset(self, callset: CallSpec):
        if callset.skippable and callset.outputs:
            raise ValueError(
                f"A callset if both skippable but has outputs {callset.outputs} for {self.class_name}"
            )
        for written in callset.written_set:
            if written not in self.input_specs:
                raise ValueError(
                    f"Written observable {written} in {self.class_name} is not an input"
                )

            # This is reflexive so don't need to redo the check in the observes loop
            if written in callset.observes:
                raise ValueError(
                    f"Written observable {written} also an observable {self.class_name} is also observable"
                )

        for observed in callset.observes:
            if observed not in self.input_specs:
                raise ValueError(
                    f"Observable {observed} in {self.class_name} is not an input"
                )

    def validate_callsets(self):
        for callset in self.callsets:
            self.validate_a_callset(callset)

    def validate_timer(self):
        if self.timer_callback is not None:
            if self.timer_callback.call.skippable:
                raise ValueError(
                    f"Signal {self.class_name} has a skippable timer callback"
                )
            self.validate_a_callset(self.timer_callback.call)

    def validate(self):
        self.validate_generics()
        self.validate_callsets()
        self.validate_timer()

    def outputs(self) -> List[str]:
        return list(self.output_specs.keys())

    @property
    def d_output_specs(self) -> Dict[str, OutputSpec]:
        return self.output_specs

    @property
    def d_input_specs(self) -> Dict[str, InputSpec]:
        return self.input_specs

    @property
    def inputs(self) -> Set[str]:
        return set(self.input_specs.keys())

    @property
    def triggering_inputs(self) -> Set[str]:
        return set(
            input
            for (input, spec) in self.d_input_specs.items()
            if not spec.non_triggering
        )


@dataclass
class Definitions(DataClassJsonMixin):
    definitions: Dict[str, Definition]
