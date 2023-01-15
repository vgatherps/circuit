from shutil import rmtree

from pycircuit.loader.loader_config import CoreLoaderConfig
from pycircuit.loader.write_circuit_call import CallStructOptions, generate_circuit_call
from pycircuit.loader.write_circuit_dot import generate_full_circuit_dot
from pycircuit.loader.write_circuit_call_dot import generate_circuit_call_dot
from pycircuit.loader.write_circuit_init import InitStructOptions, generate_circuit_init
from pycircuit.loader.write_circuit_struct import generate_circuit_struct_file
from pycircuit.loader.write_timer_call import (
    TimerCallStructOptions,
    generate_timer_call,
)

from .call_clang_format import call_clang_format
from .test_action import CircuitTestGroup, HEADER

MAIN_TEST_TARGET = "pycircuit_gen_test"

TEST_FILE = "_test_runner"


def generate_cmake_sources(target_name: str, cc_names) -> str:
    ccs = " ".join(cc_names)
    return f"target_sources({target_name} PRIVATE {ccs})"


def generate_test_in(
    tests: CircuitTestGroup,
    test_dir: str,
    test_name: str,
    core_config: CoreLoaderConfig,
):

    circuit = tests.circuit
    import os

    out_dir = f"{test_dir}/{test_name}"

    if os.path.exists(out_dir):
        rmtree(out_dir)
    os.mkdir(out_dir)

    # This could be much better abstracted...

    cc_names = [f"{TEST_FILE}.cc"]

    with open(f"{out_dir}/{TEST_FILE}.cc", "w") as test_out:
        test_out.write(call_clang_format(tests.generate_lines(test_name)))

    calls_used = set(call.call_name for test in tests.tests for call in test.calls)
    for call_name in calls_used:
        local_name = f"{call_name}.cc"
        cc_names.append(local_name)
        file_name = f"{out_dir}/{local_name}"

        options = CallStructOptions(
            struct_name=test_name,
            struct_header=HEADER,
            call_name=call_name,
        )
        content = generate_circuit_call(
            struct_options=options,
            config=core_config,
            circuit=circuit,
        )

        with open(file_name, "w") as write_to:
            write_to.write(call_clang_format(content))

        dot_content = generate_circuit_call_dot(
            struct_options=options,
            config=core_config,
            circuit=circuit,
        )

        with open(f"{out_dir}/{call_name}.dot", "w") as write_to:
            write_to.write(dot_content)

    # Fill out some timer calls
    for component in circuit.components.values():
        timer = component.definition.timer_callset
        if timer is None:
            continue
        fname = f"{component.name}_timer_callback.cc"

        cc_names.append(fname)

        call = generate_timer_call(
            TimerCallStructOptions(
                struct_name=test_name,
                struct_header=HEADER,
                component_name=component.name,
            ),
            core_config,
            circuit,
        )

        with open(f"{out_dir}/{fname}", "w") as timer_file:
            timer_file.write(call_clang_format(call))

    struct_content = generate_circuit_struct_file(
        test_name, config=core_config, circuit=circuit
    )

    with open(f"{out_dir}/{HEADER}.hh", "w") as struct_file:
        struct_file.write(call_clang_format(struct_content))

    dot_content = generate_full_circuit_dot(circuit)

    with open(f"{out_dir}/{HEADER}.dot", "w") as circuit_dot_file:
        circuit_dot_file.write(dot_content)

    init_content = generate_circuit_init(
        InitStructOptions(struct_name=test_name, struct_header=HEADER),
        config=core_config,
        circuit=circuit,
    )
    cc_names.append("init.cc")

    with open(f"{out_dir}/init.cc", "w") as init_file:
        init_file.write(call_clang_format(init_content))

    with open(f"{out_dir}/CMakeLists.txt", "w") as cmake_file:
        cmake_file.write(generate_cmake_sources(MAIN_TEST_TARGET, cc_names))
