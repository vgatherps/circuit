"""
This attempts to model a variety of signals which are all strongly correlated
and determine if something is meaningfully leading

The assumptions is that one passes in signals like:
* Book fairs
* weighed mids
* Derivatives on the underlying

Basically things that are all expected to move together

Then, for signal i, you take bounded_sum(s_{j != i}),
and discount the signal move by this sum
(i.e. remove information already known by other moves)

This gives you a vector D, and the output signal is bounded_sum(D)

I'm not convinced this contains a ton of information because of the sharp clamps
on the lead-lag, and because you'll almost always just go by the first.

Basically, there will usually only be one negative
and positive value entering D at most (others will get discounted to zero)
unless the coeficients in the bounded sum decrease magnitudes. 

However D itself sort of has the same problem. Unless the coefficients
are all pointing in different directions, you just get min/max.
As they point in different directions it becomes a more standard regression

As a dummy demonstration of the whole 'differentiable core' game,
it's quite good though. Gives a ton of parameters and operators
and mostly "just works"
"""


from typing import List, Optional, Tuple
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.regressions.bounded_sum import soft_bounded_sum
from pycircuit.circuit_builder.signals.discount_by import discount_by
from pycircuit.circuit_builder.signals.minmax import clamp


# TODO pls test this very much


def multi_symmetric_move(
    vals: List[HasOutput],
    coefficients: List[List[HasOutput]],
    post_coeffs: Optional[List[List[HasOutput]]] = None,
    scale: float = 1.0,
    discounted_clamp: Optional[float] = None,
):
    """This computes the following operations on inputs 0..i, S_i with coeffs[0..i, 0..i]:

    1. B_i = bounded_sum(S_{j != i}, coeffs[i, j != i]
    2. D_i = discount(S_i, B_i)

    return bounded_sum(D_i, coeffs[i, i])

    Both a row of coefficients and individual ones can be None:
    * A None row i implies a zero coefficient for D_i,
        so said D_i will not be computed.
    * A None coefficient j in row i implies that coefficient j in B_i will not be used
        coeffs[i, i] can never be None, otherwise the row should be None
    """
    if len(coefficients) != len(vals):
        raise ValueError(
            f"Coefficents matrix had {len(coefficients)} rows "
            f"but was passed {len(vals)} entries"
        )

    if len(vals) < 2:
        raise ValueError("Must pass at least 2 signals to multi_symmetric_move")

    def d_i_for(idx: int) -> HasOutput:
        "If the row has a coefficient returns D_i, coefficient)"
        clist = coefficients[idx]

        if len(clist) != len(vals):
            raise ValueError(
                f"Coefficients matrix row {idx} had {len(coefficients)} columns "
                f"but was passed {len(vals)} entries"
            )

        b_list = vals.copy()
        b_coeffs = clist.copy()

        b_list.pop(idx)
        b_coeffs.pop(idx)

        if post_coeffs is not None:
            plist = post_coeffs[idx].copy()
            plist.pop(idx)
            B_i = soft_bounded_sum(b_list, b_coeffs, scale=scale, post_coeffs=plist)
        else:
            B_i = soft_bounded_sum(b_list, b_coeffs, scale=scale)
        D_i = discount_by(vals[idx], B_i)

        if discounted_clamp is not None:
            return clamp(D_i, discounted_clamp)
        else:
            return D_i

    D_vec = [d_i_for(idx) for idx in range(len(vals))]

    coeffs = [coefficients[i][i] for i in range(0, len(vals))]

    if post_coeffs is not None:
        p_coeffs = [post_coeffs[i][i] for i in range(0, len(vals))]
        return soft_bounded_sum(D_vec, coeffs, scale=scale, post_coeffs=p_coeffs)
    else:
        return soft_bounded_sum(D_vec, coeffs, scale=scale)
