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

    @classmethod
    def operate(
        cls,
        single_inputs: Dict[str, CircuitTensor],
        array_inputs: Dict[str, List[Dict[str, CircuitTensor]]],
    ) -> CircuitTensor:
        assert not array_inputs

        return torch.where(
            single_inputs["select_a"],
            single_inputs["a"],
            single_inputs["b"],
        )
