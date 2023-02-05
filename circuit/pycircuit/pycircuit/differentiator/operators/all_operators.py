from typing import Dict, Type
from .binary_math_operators import create_binary, BINARY_OPERATORS
from pycircuit.differentiator.operator import OperatorFn


ALL_OPERATORS: Dict[str, Type[OperatorFn]] = {}

ALL_OPERATORS.update(BINARY_OPERATORS)
