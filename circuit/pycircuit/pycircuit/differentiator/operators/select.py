from typing import Callable, Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import CircuitTensor

import torch


class Select(OperatorFn):
    @classmethod
    def name(cls) -> str:
        return "select"

    @classmethod
    def single_inputs(cls) -> Set[str]:
        return {"a", "b", "select_a"}

    @classmethod
    def array_inputs(cls) -> Dict[str, Set[str]]:
        return {}

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)

        self.a_module = single_inputs["a"]
        self.b_module = single_inputs["b"]
        self.select_a = single_inputs["select_a"]

    def do_forward(self, tensors: List[CircuitTensor]):
        return torch.where(
            tensors[self.select_a], tensors[self.a_module], tensors[self.b_module]
        )
