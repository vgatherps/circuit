from dataclasses import dataclass
from shutil import rmtree
from typing import Dict

from argparse_dataclass import ArgumentParser
from pycircuit.circuit_builder.circuit import (
    CallGroup,
    CircuitBuilder,
    ComponentOutput,
    OutputOptions,
)
from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.circuit_builder.circuit import CallStruct
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.test_generator.generate_single_test import generate_test_in

from .test_action import (
    CircuitTest,
    CircuitTestGroup,
    EqLit,
    TriggerCall,
    TriggerVal,
)

MAIN_TEST_TARGET = "pycircuit_gen_test"


def generate_cmake_sources(target_name: str, cc_names) -> str:
    ccs = " ".join(cc_names)
    return f"target_sources({target_name} PRIVATE {ccs})"


def generate_all_tests(
    all_tests: Dict[str, CircuitTestGroup],
    global_test_dir: str,
    core_config: CoreLoaderConfig,
):

    for (test_name, test_cases) in all_tests.items():
        generate_test_in(test_cases, global_test_dir, test_name, core_config)

    subdirs = list(all_tests.keys())

    cmake_lines = "\n".join(f"add_subdirectory({test_dir})" for test_dir in subdirs)

    with open(f"{global_test_dir}/CMakeLists.txt", "w") as cmake_file:
        cmake_file.write(cmake_lines)


def test_circuit() -> CircuitTestGroup:

    circuit = CircuitBuilder({})

    with CircuitContextManager(circuit):
        ext_1 = circuit.get_external("a", "int")
        ext_2 = circuit.get_external("b", "int")

        added = ext_1 + ext_2

        added.output_options["out"] = OutputOptions(force_stored=True)
        circuit.rename_component(added, "add_out")

    trigger = CallGroup("AddAB", {"a": "a", "b": "b"})

    circuit.add_call_struct("AddAB", CallStruct.from_inputs(a="int", b="int"))
    circuit.add_call_group("trigger_add", trigger)

    call = TriggerCall(
        values=[TriggerVal("1", "a", "int"), TriggerVal("2", "b", "int")],
        time=10,
        trigger=trigger,
        call_name="trigger_add",
        checks=[EqLit(output=ComponentOutput("add_out", "out"), eq_to="3", type="int")],
    )

    test = CircuitTest(calls=[call], group="add_tests", name="add_works_both_triggered")

    return CircuitTestGroup(tests=[test], circuit=circuit)


@dataclass
class TestGenOptions:
    out_dir: str


def main():

    import sys

    args = ArgumentParser(TestGenOptions).parse_args(sys.argv[1:])

    import os

    if os.path.exists(args.out_dir):
        rmtree(args.out_dir)
    os.mkdir(args.out_dir)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    loader_config_str = open(f"{dir_path}/loader.json").read()
    core_config = CoreLoaderConfig.from_json(loader_config_str)

    circuit_test = test_circuit()

    generate_all_tests({"add_test": circuit_test}, args.out_dir, core_config)


if __name__ == "__main__":
    main()
