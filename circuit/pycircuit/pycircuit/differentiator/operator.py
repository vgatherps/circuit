from abc import ABC, abstractmethod
from typing import Dict, List, Set

from .tensor import CircuitTensor


class OperatorFn(ABC):
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def single_inputs(cls) -> Set[str]:
        pass

    @classmethod
    @abstractmethod
    def array_inputs(cls) -> Dict[str, Set[str]]:
        pass

    @classmethod
    @abstractmethod
    def operate(
        cls,
        single_inputs: Dict[str, CircuitTensor],
        array_inputs: Dict[str, List[Dict[str, CircuitTensor]]],
    ) -> CircuitTensor:
        pass

    @classmethod
    def compute(
        cls,
        single_inputs: Dict[str, CircuitTensor],
        array_inputs: Dict[str, List[Dict[str, CircuitTensor]]],
    ) -> CircuitTensor:
        expected_single = cls.single_inputs()
        expected_array_dict = cls.array_inputs()
        expected_array = set(expected_array_dict.keys())

        has_single = set(single_inputs.keys())
        has_array = set(array_inputs.keys())

        if expected_single != has_single:
            raise ValueError(
                f"Tensor operator {cls.name()} got single inputs {has_single} "
                f"but expected {expected_single}"
            )

        if expected_array != has_array:
            raise ValueError(
                f"Tensor operator {cls.name()} got array inputs {has_array} "
                f"but expected {expected_array}"
            )

        for (batch_name, batch) in expected_array_dict.items():
            list_of_batches = array_inputs[batch_name]
            for in_batch in list_of_batches:
                in_keys = set(in_batch.keys())
                if in_keys != batch:
                    raise ValueError(
                        f"Array input had input batch with keys {in_keys} "
                        f"but expected {batch}"
                    )

        return cls.operate(single_inputs, array_inputs)
