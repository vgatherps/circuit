from dataclasses import dataclass
from typing import List, Optional
from pycircuit.circuit_builder.component import Component, ComponentOutput
from pycircuit.cpp_codegen.type_names import (
    generate_output_type_alias_name,
    get_alias_for,
)
from pycircuit.cpp_codegen.generation_metadata import AnnotatedComponent
from pycircuit.cpp_codegen.generation_metadata import OutputMetadata


def generate_local_output_ref_name(component_name: str, output_name: str) -> str:
    return f"{component_name}_{output_name}"


@dataclass
class OutputGenerator:
    annotated_component: AnnotatedComponent
    output_name: str

    def component(self) -> Component:
        return self.annotated_component.component

    def output(self) -> ComponentOutput:
        return ComponentOutput(
            parent=self.component().name, output_name=self.output_name
        )

    def output_var_type_alias(self) -> str:
        return generate_output_type_alias_name(self.component().name, self.output_name)

    def output_metadata(self) -> OutputMetadata:
        return self.annotated_component.output_data[self.output_name]

    def generate_output_ref_init_lines(self) -> List[str]:
        output_metadata = self.output_metadata()

        definition = self.annotated_component.component.definition
        name = self.component().name
        class_name = get_alias_for(self.component())

        output_specs = definition.d_output_specs[self.output_name]
        output_class = output_specs.type_path
        type_header = f"{class_name}::{output_class}"
        var_name = generate_local_output_ref_name(name, self.output_name)

        reference_header = f"{type_header}& {var_name}"

        if output_metadata.is_value_ephemeral:

            init_var_name = f"{var_name}_EV__"
            return [
                f"{type_header} {init_var_name}{output_specs.get_ctor()};",
                f"{reference_header} = {init_var_name};",
            ]
        else:
            return [f"{reference_header} = _outputs.{name}_{self.output_name};"]

    def get_valid_path(self) -> str:
        output_metadata = self.annotated_component.output_data[self.output_name]
        if output_metadata.validity_index is None:
            return f"{self.component().name}_{self.output_name}_IV"
        else:
            return f"outputs_is_valid[{output_metadata.validity_index}]"

    def generate_is_valid_init(self) -> List[str]:

        # This is already correct for always-invalid outputs
        output_metadata = self.annotated_component.output_data[self.output_name]
        if output_metadata.validity_index is None:
            if self.annotated_component.component.definition.d_output_specs[
                self.output_name
            ].always_valid:
                valid_value = "true"
                valid_prefix = "constexpr bool"
            else:
                valid_value = "false"
                valid_prefix = "bool"

            valid_path = self.get_valid_path()
            return [f"{valid_prefix} {valid_path} = {valid_value};"]
        return []
