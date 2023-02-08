from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.component import Component
from ..minmax import max_of
from ..unary_arithmetic import cexp
from ..constant import make_double


def id(input: HasOutput) -> HasOutput:
    return input


linear = id


# TODO give there their own components and dedicated torch operations


def sigmoid(input: HasOutput) -> Component:
    one = make_double(1)
    return one / (one + cexp(-input))


def tanh(input: HasOutput) -> Component:
    the_sigmoid = sigmoid(input)

    return make_double(2) * the_sigmoid - make_double(1)


def relu(input: HasOutput) -> Component:
    zero = make_double(0)
    return max_of(input, zero)
