from abc import abstractmethod
from typing import Dict, List, Set, Type
from pycircuit.differentiator.operator import OperatorFn
from pycircuit.differentiator.tensor import (
    tensor_max,
    tensor_min,
    CircuitTensor,
)


class BinaryOp(OperatorFn):
    @classmethod
    def single_inputs(cls) -> Set[str]:
        return {"a", "b"}

    @classmethod
    def array_inputs(cls) -> Dict[str, Set[str]]:
        return {}

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        OperatorFn.__init__(self, single_inputs, array_inputs, fill_idx)
        assert not array_inputs
        self.a_module = single_inputs["a"]
        self.b_module = single_inputs["b"]

    @classmethod
    @abstractmethod
    def do_op(cls, a: CircuitTensor, b: CircuitTensor) -> CircuitTensor:
        pass

    def do_forward(self, tensors: List[CircuitTensor]) -> CircuitTensor:
        return self.do_op(tensors[self.a_module], tensors[self.b_module])


class Add(BinaryOp):
    @classmethod
    def name():
        return "add"

    @classmethod
    def do_op(self, a, b) -> CircuitTensor:
        return a + b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Sub(BinaryOp):
    @classmethod
    def name():
        return "sub"

    @classmethod
    def do_op(siwclslf, a, b) -> CircuitTensor:
        return a - b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Mul(BinaryOp):
    @classmethod
    def name():
        return "mul"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a * b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Div(BinaryOp):
    @classmethod
    def name():
        return "div"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a / b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Lt(BinaryOp):
    @classmethod
    def name():
        return "lt"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a < b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Le(BinaryOp):
    @classmethod
    def name():
        return "le"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a <= b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Gt(BinaryOp):
    @classmethod
    def name():
        return "gt"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a > b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Ge(BinaryOp):
    @classmethod
    def name():
        return "ge"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return a >= b

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Min(BinaryOp):
    @classmethod
    def name():
        return "min"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return tensor_min(a, b)

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


class Max(BinaryOp):
    @classmethod
    def name():
        return "max"

    @classmethod
    def do_op(cls, a, b) -> CircuitTensor:
        return tensor_max(a, b)

    def __init__(
        self,
        single_inputs: Dict[str, int],
        array_inputs: Dict[str, List[Dict[str, int]]],
        fill_idx: int,
    ):
        super().__init__(single_inputs, array_inputs, fill_idx)


BINARY_OPERATORS: Dict[str, Type[OperatorFn]] = {
    "add": Add,
    "sub": Sub,
    "mul": Mul,
    "div": Div,
    "lt": Lt,
    "le": Le,
    "gt": Gt,
    "ge": Ge,
    "min": Min,
    "max": Max,
}
