from typing import Callable, Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import CircuitTensor
from pycircuit.differentiator.tensor import tensor_max, tensor_min

import torch


UnaryOp = Callable[[CircuitTensor], CircuitTensor]


def create_unary(name: str, op: UnaryOp) -> Type[OperatorFn]:
    class ABinaryOp(OperatorFn):
        @classmethod
        def name(cls) -> str:
            return name

        @classmethod
        def single_inputs(cls) -> Set[str]:
            return {"a"}

        @classmethod
        def array_inputs(cls) -> Dict[str, Set[str]]:
            return {}

        @classmethod
        def operate(
            cls,
            single_inputs: Dict[str, CircuitTensor],
            array_inputs: Dict[str, List[Dict[str, CircuitTensor]]],
        ) -> CircuitTensor:
            assert not array_inputs
            return op(single_inputs["a"])

    return ABinaryOp


def _exp_t(a: CircuitTensor) -> CircuitTensor:
    return torch.exp(a)


def _log_t(a: CircuitTensor) -> CircuitTensor:
    return torch.log(a)


def _abs_t(a: CircuitTensor) -> CircuitTensor:
    return torch.abs(a)


UNARY_OPERATORS = {
    "exp": create_unary("exp", _exp_t),
    "log": create_unary("log", _log_t),
    "abs": create_unary("abs", _abs_t),
}
