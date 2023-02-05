from typing import Callable, Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import CircuitTensor
from pycircuit.differentiator.tensor import tensor_max, tensor_min


BinaryOp = Callable[[CircuitTensor, CircuitTensor], CircuitTensor]


def create_binary(name: str, op: BinaryOp) -> Type[OperatorFn]:
    class ABinaryOp(OperatorFn):
        @classmethod
        def name(cls) -> str:
            return name

        @classmethod
        def single_inputs(cls) -> Set[str]:
            return {"a", "b"}

        @classmethod
        def array_inputs(cls) -> Set[str]:
            return set()

        @classmethod
        def operate(
            cls,
            single_inputs: Dict[str, CircuitTensor],
            array_inputs: Dict[str, List[CircuitTensor]],
        ) -> CircuitTensor:
            assert len(array_inputs) == 0
            return op(single_inputs["a"], single_inputs["b"])

    return ABinaryOp


def _add_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a + b


def _sub_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a - b


def _mul_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a * b


def _div_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a / b


def _lt_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a < b


def _le_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a <= b


def _gt_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a > b


def _ge_t(a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
    return a >= b


BINARY_OPERATORS = {
    "add": create_binary("add", _add_t),
    "sub": create_binary("sub", _sub_t),
    "mul": create_binary("mul", _mul_t),
    "div": create_binary("div", _div_t),
    "lt": create_binary("lt", _lt_t),
    "le": create_binary("le", _le_t),
    "gt": create_binary("gt", _gt_t),
    "ge": create_binary("ge", _ge_t),
    "min": create_binary("min", tensor_min),
    "max": create_binary("max", tensor_max),
}
