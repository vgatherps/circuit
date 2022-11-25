import pytest
from frozendict import frozendict
from pycircuit.circuit_builder.circuit import ComponentOutput, OutputOptions
from pycircuit.cpp_codegen.generation_metadata import (
    OutputMetadata,
    generate_output_metadata_for,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    basic_component,
)


@pytest.mark.parametrize("initial_non_ephemeral", [0, 1, 2, 3])
def test_output_metadata_non_loaded(initial_non_ephemeral):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component, set(), initial_non_ephemeral
    )

    metadata_f = frozendict(metadata)

    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=None),
            OUT_B: OutputMetadata(validity_index=initial_non_ephemeral),
        }
    )

    assert count == initial_non_ephemeral + 1


@pytest.mark.parametrize("initial_non_ephemeral", [0, 1])
def test_output_metadata_non_ephemeral_loaded(initial_non_ephemeral):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component,
        set([ComponentOutput(parent=COMPONENT_NAME, output=OUT_B)]),
        initial_non_ephemeral,
    )

    metadata_f = frozendict(metadata)

    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=None),
            OUT_B: OutputMetadata(validity_index=initial_non_ephemeral),
        }
    )

    assert count == initial_non_ephemeral + 1


@pytest.mark.parametrize("initial_non_ephemeral", [0, 1])
def test_output_metadata_ephemeral_loaded(initial_non_ephemeral):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component,
        set([ComponentOutput(parent=COMPONENT_NAME, output=OUT_A)]),
        initial_non_ephemeral,
    )

    metadata_f = frozendict(metadata)

    # This passes tests - iirc python guarantees iteration order is insertion order now?
    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=initial_non_ephemeral),
            OUT_B: OutputMetadata(validity_index=initial_non_ephemeral + 1),
        }
    )

    assert count == initial_non_ephemeral + 2


@pytest.mark.parametrize("initial_non_ephemeral", [0, 1])
def test_output_metadata_ephemeral_force_stored(initial_non_ephemeral):
    component = basic_component()

    component.output_options[OUT_A] = OutputOptions(force_stored=True)

    metadata, count = generate_output_metadata_for(
        component,
        set(),
        initial_non_ephemeral,
    )

    metadata_f = frozendict(metadata)

    # This passes tests - iirc python guarantees iteration order is insertion order now?
    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=initial_non_ephemeral),
            OUT_B: OutputMetadata(validity_index=initial_non_ephemeral + 1),
        }
    )

    assert count == initial_non_ephemeral + 2
