import pytest
from frozendict import frozendict
from pycircuit.circuit_builder.component import ComponentOutput, OutputOptions
from pycircuit.cpp_codegen.generation_metadata import (
    OutputMetadata,
    generate_output_metadata_for,
)
from pycircuit.cpp_codegen.test.test_common import (
    COMPONENT_NAME,
    OUT_A,
    OUT_B,
    OUT_C,
    basic_component,
)


@pytest.mark.parametrize("initial_validity_required", [0, 1])
def test_output_metadata_non_loaded(initial_validity_required):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component, set(), initial_validity_required
    )

    metadata_f = frozendict(metadata)

    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=None, is_value_ephemeral=True),
            OUT_B: OutputMetadata(
                validity_index=initial_validity_required, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(validity_index=None, is_value_ephemeral=True),
        }
    )

    assert count == initial_validity_required + 1


@pytest.mark.parametrize("initial_validity_required", [0, 1])
def test_output_metadata_non_ephemeral_loaded(initial_validity_required):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component,
        set([ComponentOutput(parent=COMPONENT_NAME, output_name=OUT_B)]),
        initial_validity_required,
    )

    metadata_f = frozendict(metadata)

    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=None, is_value_ephemeral=True),
            OUT_B: OutputMetadata(
                validity_index=initial_validity_required, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(validity_index=None, is_value_ephemeral=True),
        }
    )

    assert count == initial_validity_required + 1


@pytest.mark.parametrize("initial_validity_required", [0, 1])
def test_output_metadata_ephemeral_loaded(initial_validity_required):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component,
        set([ComponentOutput(parent=COMPONENT_NAME, output_name=OUT_A)]),
        initial_validity_required,
    )

    metadata_f = frozendict(metadata)

    # This passes tests - iirc python guarantees iteration order is insertion order now?
    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(
                validity_index=initial_validity_required, is_value_ephemeral=False
            ),
            OUT_B: OutputMetadata(
                validity_index=initial_validity_required + 1, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(validity_index=None, is_value_ephemeral=True),
        }
    )

    assert count == initial_validity_required + 2


@pytest.mark.parametrize("initial_validity_required", [0, 1])
def test_output_metadata_ephemeral_force_stored(initial_validity_required):
    component = basic_component()

    component.output_options[OUT_A] = OutputOptions(force_stored=True)

    metadata, count = generate_output_metadata_for(
        component,
        set(),
        initial_validity_required,
    )

    metadata_f = frozendict(metadata)

    # This passes tests - iirc python guarantees iteration order is insertion order now?
    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(
                validity_index=initial_validity_required, is_value_ephemeral=False
            ),
            OUT_B: OutputMetadata(
                validity_index=initial_validity_required + 1, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(validity_index=None, is_value_ephemeral=True),
        }
    )

    assert count == initial_validity_required + 2


@pytest.mark.parametrize("initial_validity_required", [0, 1])
def test_output_metadata_always_valid_loaded(initial_validity_required):
    component = basic_component()

    metadata, count = generate_output_metadata_for(
        component,
        set([ComponentOutput(parent=COMPONENT_NAME, output_name=OUT_C)]),
        initial_validity_required,
    )

    metadata_f = frozendict(metadata)

    assert metadata_f == frozendict(
        {
            OUT_A: OutputMetadata(validity_index=None, is_value_ephemeral=True),
            OUT_B: OutputMetadata(
                validity_index=initial_validity_required, is_value_ephemeral=False
            ),
            OUT_C: OutputMetadata(validity_index=None, is_value_ephemeral=False),
        }
    )

    assert count == initial_validity_required + 1
