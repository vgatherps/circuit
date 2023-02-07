from typing import List, Optional, TypeAlias
import torch
import torch.random

CircuitTensor: TypeAlias = torch.Tensor
CircuitParameter: TypeAlias = torch.nn.parameter.Parameter
Module: TypeAlias = torch.nn.Module


def tensor_min(a: CircuitTensor, b: CircuitTensor):
    return torch.minimum(a, b)


def tensor_max(a: CircuitTensor, b: CircuitTensor):
    return torch.maximum(a, b)


def make_parameter(initial_value: Optional[CircuitTensor] = None):
    # Mypy is weird about this optional parameter
    if initial_value is None:
        initial_value = torch.rand(1)
    return CircuitParameter(data=initial_value, requires_grad=True)


def make_constant(value: float | List[float]) -> CircuitTensor:
    if isinstance(value, float):
        value = [value]
    return CircuitTensor(value)


def make_empty() -> CircuitTensor:
    return CircuitTensor()


def just_return_module(x: CircuitTensor) -> Module:
    class JustRet(Module):
        def __init__(self, x: CircuitTensor):
            super(self).__init__()
            self.rval = x

        def forward():
            return x

    return JustRet(x)
