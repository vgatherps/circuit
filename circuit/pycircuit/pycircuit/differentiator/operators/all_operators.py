from typing import Dict, Type

from .binary_math_operators import BINARY_OPERATORS
from .unary_math_operators import UNARY_OPERATORS
from .summary_operators import SUMMARY_OPERATORS
from .select import Select
from pycircuit.differentiator.operator import OperatorFn


ALL_OPERATORS: Dict[str, Type[OperatorFn]] = {"select": Select}

ALL_OPERATORS.update(BINARY_OPERATORS)
ALL_OPERATORS.update(UNARY_OPERATORS)
ALL_OPERATORS.update(SUMMARY_OPERATORS)
