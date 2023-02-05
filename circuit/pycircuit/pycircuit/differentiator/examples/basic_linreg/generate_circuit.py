from dataclasses import dataclass
from pycircuit.circuit_builder.circuit import CircuitBuilder, CircuitData
from pycircuit.circuit_builder.component import ComponentOutput
from pycircuit.circuit_builder.circuit_context import CircuitContextManager


@dataclass
class Generated:
    circuit: CircuitData
    regress: ComponentOutput


def create_linreg_circuit() -> Generated:
    # The basic math operations are built in
    builder = CircuitBuilder({})

    with CircuitContextManager(builder):

        x = builder.get_external("x", "double")
        y = builder.get_external("y", "double")

        x_factor = builder.make_parameter("x_factor")
        y_factor = builder.make_parameter("y_factor")

        regress = (x * x_factor) + (y * y_factor)

        return Generated(circuit=builder, regress=regress.output())
