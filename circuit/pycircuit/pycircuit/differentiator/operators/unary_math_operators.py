from abc import abstractmethod
from typing import Callable, Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import CircuitTensor
from pycircuit.differentiator.tensor import tensor_max, tensor_min

import torch


class AUnaryOp(OperatorFn):
    @classmethod
    def single_inputs(cls) -> Set[str]:
        return {"a"}

    @classmethod
    def array_inputs(cls) -> Dict[str, Set[str]]:
        return {}

    @classmethod
    @abstractmethod
    def do_op(cls, a: CircuitTensor) -> CircuitTensor:
        pass

    def do_forward(self, tensors: List[CircuitTensor]):
        return self.do_op(tensors[self.a_module])

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(AUnaryOp, self).__init__(single_inputs, array_inputs, fill_idx)
        self.a_module = single_inputs["a"]


class Exp(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "exp"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Exp, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return torch.exp(a)


class Log(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "log"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Log, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return torch.log(a)


class Sqrt(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "sqrt"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Sqrt, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return torch.sqrt(a)


class Abs(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "abs"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Abs, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return torch.abs(a)


class Neg(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "neg"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Neg, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return -a


UNARY_OPERATORS: Dict[str, Type[OperatorFn]] = {
    "exp": Exp,
    "log": Log,
    "abs": Abs,
    "neg": Neg,
    "sqrt": Sqrt,
}
