from typing import List
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.minmax import max_of, min_of
from .tree_sum import tree_max, tree_min, tree_sum

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

    factored = [val * factor for (val, factor) in zip(vals, factors)]

    sum_of = tree_sum(factored)

    raw_max = tree_max(vals)
    raw_min = tree_min(vals)

    return max_of(raw_min, min_of(raw_max, sum_of))
