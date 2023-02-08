from dataclasses import dataclass
from typing import List, Optional
from pycircuit.circuit_builder.circuit import HasOutput
from ..tree_sum import tree_sum


@dataclass
class LinReg:
    factors: List[HasOutput]
    bias: Optional[HasOutput] = None

    def regress(self, vals: List[HasOutput]) -> HasOutput:
        return linreg(vals, self)


def linreg(vals: List[HasOutput], reg: LinReg) -> HasOutput:
    if len(vals) != len(reg.factors):
        raise ValueError(
            f"Values list has length {len(vals)} and factors length {len(reg.factors)}"
        )

    match vals:
        case []:
            raise ValueError("Values list has zero length")
        case [_]:
            weighted = vals[0] * reg.factors[0]
        case [*_]:
            factored = [val * factor for (val, factor) in zip(vals, reg.factors)]
            weighted = tree_sum(factored)

    if reg.bias is not None:
        return weighted + reg.bias
    else:
        return weighted
