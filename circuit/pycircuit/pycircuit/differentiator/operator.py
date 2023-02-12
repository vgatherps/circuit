from abc import ABC, abstractmethod
from typing import Dict, List, Set

from pycircuit.circuit_builder.component import ComponentOutput

from .tensor import CircuitTensor
import torch

VERBOSE = False


class OperatorFn(ABC, torch.nn.Module):
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

    @abstractmethod
    def do_forward(self, tensors: List[CircuitTensor]):
        pass

    # need to refactor this to not have hacks

    def set_output(self, output: ComponentOutput):
        self.output = output

    def forward(self, tensors: List[CircuitTensor]):
        rval = self.do_forward(tensors)
        if VERBOSE:
            inputs = {name: tensors[idx] for (name, idx) in self.single_mapping.items()}
            if self.output is not None:
                print(
                    f"Operator {self.name()} "
                    f"output {self.output.parent}::{self.output.output_name} "
                    f"returns {rval.detach().numpy()}"
                )
            else:
                print(f"Operator {self.name()} returns {rval.detach().numpy()}")
            print("Taking:")
            for (name, input) in inputs.items():
                print(f"Input {name}: {input.detach().numpy()}")
            print()
            print()
        tensors[self.fill_idx] = rval
        return rval

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super(OperatorFn, self).__init__()

        self.fill_idx = fill_idx

        self.output = None

        self.single_mapping = single_inputs
        self.array_mapping = array_inputs

        expected_single = self.single_inputs()
        expected_array_dict = self.array_inputs()
        expected_array = set(expected_array_dict.keys())

        has_single = set(single_inputs.keys())
        has_array = set(array_inputs.keys())

        if expected_single != has_single:
            raise ValueError(
                f"Tensor operator {self.name()} got single inputs {has_single} "
                f"but expected {expected_single}"
            )

        if expected_array != has_array:
            raise ValueError(
                f"Tensor operator {self.name()} got array inputs {has_array} "
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


class DagOperator(torch.nn.Module):
    def __init__(self, storage: List[CircuitTensor], ordered: List[OperatorFn]):
        super(DagOperator, self).__init__()

        self.storage = storage
        self.ordered = ordered

    def forward(self):

        for operator in self.ordered:
            last_returned = operator.forward(self.storage)

        assert last_returned is self.storage[-1]
        return last_returned
