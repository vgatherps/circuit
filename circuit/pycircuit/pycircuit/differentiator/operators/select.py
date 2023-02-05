from typing import Callable, Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import CircuitTensor

import tensorflow as tf


class Select(OperatorFn):
    @classmethod
    def name(cls) -> str:
        return "select"

    @classmethod
    def single_inputs(cls) -> Set[str]:
        return {"a", "b", "select_a"}

    @classmethod
    def array_inputs(cls) -> Set[str]:
        return set()

    @classmethod
    def operate(
        cls,
        single_inputs: Dict[str, CircuitTensor],
        array_inputs: Dict[str, List[CircuitTensor]],
    ) -> CircuitTensor:
        assert not array_inputs

        return tf.where(
            condition=single_inputs["select_a"],
            x=single_inputs["a"],
            y=single_inputs["b"],
        )
