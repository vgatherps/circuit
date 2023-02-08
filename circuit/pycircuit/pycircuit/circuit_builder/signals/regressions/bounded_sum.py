from typing import List, Optional
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.constant import make_double
from pycircuit.circuit_builder.signals.regressions.linreg import LinReg
from ..minmax import max_of, min_of
from ..tree_sum import tree_max, tree_min, tree_sum
from ..unary_arithmetic import cexp, cabs

# TODO consider if this should be replaced be some sort of more standard operator
# i.e. some sort of scaled sigmoid or softmax selector.
# This operator is *much* faster than the above ones, however,
# and has fewer parameters

# Linearly regress the inputs, and clamp by the minimum and maximum
# This is not terribly well behaved with negative factors - those allow
# you to escape the bounds
#
# This operator makes the most sense when considering inputs that tend to be correlated
# i.e. returns of a book fair on BTC/USDT perp and BTC/USDT spot.
# It can almost be thought of as a sort of lead-lag selector
# When everything moves in one direction, you just select the min/max anyways
# However when there's disagreement, this starts reverting to a standard linear regression
def bounded_sum(vals: List[HasOutput], factors: List[HasOutput]):
    if len(vals) != len(factors):
        raise ValueError(
            f"Values list has length {len(vals)} and factors length {len(factors)}"
        )

    if len(vals) == 0:
        raise ValueError("Values list has zero length")

    sum_of = LinReg(factors).regress(vals)

    raw_max = tree_max(vals)
    raw_min = tree_min(vals)

    return max_of(raw_min, min_of(raw_max, sum_of))


def soft_bounded_sum(
    vals: List[HasOutput],
    factors: List[HasOutput],
    scale: float = 1.0,
    post_coeffs: Optional[List[HasOutput]] = None,
):
    """
    Uses soft_max to weight the individual outputs
    and sums weighted by said outputs

    For small inputs (relative to weights)
    like returns, feels like this is just a
    linear regression weighted by the value itself?
    Any reason to have this fancy exp involvement?
    """
    if len(vals) != len(factors):
        raise ValueError(
            f"Values list has length {len(vals)} and factors length {len(factors)}"
        )

    if post_coeffs is not None and len(post_coeffs) != len(vals):
        raise ValueError(
            f"Post sum coefficients list has length {len(post_coeffs)} and values length {len(vals)}"
        )

    if len(vals) == 0:
        raise ValueError("Values list has zero length")

    cscale = make_double(scale)

    exp_for_max = [
        cexp(factors[i] * (cscale * cabs(vals[i]))) for i in range(0, len(vals))
    ]

    sum = tree_sum(exp_for_max)

    weights = [exp_for_max[i] / sum for i in range(0, len(vals))]

    summands = [weights[i] * vals[i] for i in range(0, len(vals))]

    if post_coeffs is not None:
        summands = [summands[i] * post_coeffs[i] for i in range(0, len(vals))]

    return tree_sum(summands)
