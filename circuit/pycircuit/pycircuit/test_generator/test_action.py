from dataclasses import dataclass
from typing import List, Union


from pycircuit.circuit_builder.circuit import CallGroup
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.circuit import CircuitData


CIRCUIT_NAME = "_the_circuit_"

HEADER = "test"


@dataclass
class EqLit:
    output: ComponentOutput
    eq_to: str
    type: str

    def generate_lines(self) -> str:
        # Todo allow caching of lookups to tests run faster
        return f"""\
{{
    OutputHandle<{self.type}> __handle__ = {CIRCUIT_NAME}.load_component_output<{self.type}>(
        "{self.output.parent}",
        "{self.output.output_name}"
    );

    optional_reference<const {self.type}> __handle_ref__ = {CIRCUIT_NAME}.load_from_handle(__handle__);

    EXPECT_TRUE(__handle_ref__.valid()) << "Could not load output {self.output.output_name} of component {self.output.parent}";
    EXPECT_EQ(({self.eq_to}), *__handle_ref__)  << "output {self.output.output_name} of component {self.output.parent} != {self.eq_to}";
}}"""


@dataclass
class EqValidOutput:
    output_a: ComponentOutput
    output_b: ComponentOutput
    type: str

    def generate_lines(self) -> str:
        raise NotImplementedError("not")


OutputCheck = Union[EqLit, EqValidOutput]


@dataclass
class TriggerVal:
    ctor: str
    name: str
    type: str


@dataclass
class TriggerCall:
    values: List[TriggerVal]
    time: int
    trigger: CallGroup
    call_name: str
    checks: List[OutputCheck]

    def generate_lines(self, struct_name: str) -> str:
        struct_lines = ",\n".join(
            f".{value.name} = Optionally<{value.type}>::Optional({value.ctor})"
            for value in self.values
        )

        check_lines = "\n\n".join(check.generate_lines() for check in self.checks)

        input_struct_type = f"{struct_name}::InputTypes::{self.trigger.struct}"
        return f"""\
{{
    {input_struct_type} _trigger_ = {{
        {struct_lines}
    }};

    DiscoveredCallback<{input_struct_type}> __call__V = {CIRCUIT_NAME}.load_callback<{input_struct_type}>("{self.call_name}");
    auto __call__ = std::get<CircuitCall<{input_struct_type}>>(__call__V);
    __call__(&{CIRCUIT_NAME}, {self.time}, _trigger_, RawCall<const Circuit *>());

    {check_lines}
}}"""


@dataclass
class CircuitTest:
    calls: List[TriggerCall]
    group: str
    name: str

    def generate_lines(self, struct_name: str) -> str:
        case_lines = "\n\n".join(
            call.generate_lines(struct_name) for call in self.calls
        )
        return f"""\
TEST({self.group}, {self.name}) {{
    {struct_name} {CIRCUIT_NAME}(nlohmann::json{{}});

    {case_lines}
}}"""


@dataclass
class CircuitTestGroup:
    tests: List[CircuitTest]
    circuit: CircuitData

    def generate_lines(self, struct_name: str):

        test_cases = "\n\n".join(
            test.generate_lines(struct_name) for test in self.tests
        )

        return f"""\
#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include <functional>

#include "{HEADER}.hh"

{test_cases}"""
