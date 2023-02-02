from dataclasses import dataclass
from typing import List, Sequence, Set

from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.cpp_codegen.generation_metadata import GenerationMetadata
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.cpp_codegen.call_generation.call_context.output_generator import (
    OutputGenerator,
)

from pycircuit.cpp_codegen.call_generation.call_data import CallGen


@dataclass
class RecordInfo:
    lines: List[str]
    description: str


BRACE_OPEN = RecordInfo(lines=["{"], description="brace open")

BRACE_CLOSE = RecordInfo(lines=["}"], description="brace close")


class CallContext:
    def __init__(self, metadata: GenerationMetadata):
        self._metadata = metadata
        self.lines: List[RecordInfo] = []
        self.generated_outputs: Set[ComponentOutput] = set()

    def append_lines(self, lines: RecordInfo):
        self.lines.append(lines)

    def register_output(self, output: ComponentOutput) -> OutputGenerator:

        # TODO handle external outputs

        generator = OutputGenerator(
            annotated_component=self._metadata.annotated_components[output.parent],
            output_name=output.output_name,
        )

        if output not in self.generated_outputs:
            self.lines.append(
                RecordInfo(
                    lines=generator.generate_is_valid_init(),
                    description=f"{output.parent}::{output.output_name} valid init",
                )
            )
            self.lines.append(
                RecordInfo(
                    lines=generator.generate_output_ref_init_lines(),
                    description=f"{output.parent}::{output.output_name} output_ref_init",
                )
            )

            self.generated_outputs.add(output)

        return generator

    def add_a_call(self, call_gen: CallGen):

        return_type = None

        for call in call_gen.call_datas:
            requested_type = call.static_return_type
            if requested_type is not None:
                if return_type is not None:
                    raise ValueError(
                        "Multiple call data generators requested a return type"
                    )

                return_type = requested_type

        call_params = ",".join(
            call_param
            for call in call_gen.call_datas
            for call_param in call.call_params
        )

        full_invocation = f"{call_gen.call_path}({call_params})"

        if return_type is not None:
            call_line = (
                f"{return_type.return_type} {return_type.name} = {full_invocation};"
            )
        else:
            call_line = f"{full_invocation};"

        for call in call_gen.call_datas:
            for output in call.outputs:
                self.register_output(output)

        with self:
            self.lines += [
                RecordInfo(
                    lines=[call.local_prefix for call in call_gen.call_datas],
                    description=f"{call_gen.call_path} local prefix",
                ),
                RecordInfo(
                    lines=[call_line], description=f"{call_gen.call_path} call line"
                ),
                RecordInfo(
                    lines=[call.local_postfix for call in call_gen.call_datas],
                    description=f"{call_gen.call_path} local postfix",
                ),
            ]

    def __enter__(self):
        self.lines.append(BRACE_OPEN)

    def __exit__(self, *args, **kwargs):
        self.lines.append(BRACE_CLOSE)

    def generate(self) -> str:
        all_lines = []

        for line in self.lines:

            local_line = "\n".join(line.lines)

            formatted_local = f"""\
/*
{line.description}
*/

{local_line}"""

            all_lines.append(formatted_local)

        return "\n\n".join(all_lines)
