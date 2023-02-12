from typing import Dict, List, Type
from pycircuit.differentiator.operators.unary_math_operators import AUnaryOp

import torch

from pycircuit.differentiator.operator import OperatorFn


class Mean(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "mean"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Mean, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        return torch.mean(a)


class Std(AUnaryOp):
    @classmethod
    def name(cls) -> str:
        return "std"

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(Std, self).__init__(single_inputs, array_inputs, fill_idx)

    @classmethod
    def do_op(self, a):
        if len(a) <= 1:
            return torch.tensor([1])
        return torch.std(a)


SUMMARY_OPERATORS: Dict[str, Type[OperatorFn]] = {
    "mean": Mean,
    "std": Std,
}
