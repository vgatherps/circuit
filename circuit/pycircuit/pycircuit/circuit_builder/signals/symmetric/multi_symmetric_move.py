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
it's quite good though
"""


from typing import List, Optional, Tuple
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.bounded_sum import bounded_sum
from pycircuit.circuit_builder.signals.discount_by import discount_by


# TODO pls test this very much


def multi_symmetric_move(
    vals: List[HasOutput],
    coefficients: List[Optional[List[Optional[HasOutput]]]],
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

    def d_i_for(idx: int) -> Optional[Tuple[HasOutput, HasOutput]]:
        "If the row has a coefficient returns D_i, coefficient)"
        clist = coefficients[idx]

        if clist is None:
            return None

        if len(clist) != len(vals):
            raise ValueError(
                f"Coefficients matrix row {idx} had {len(coefficients)} columns "
                f"but was passed {len(vals)} entries"
            )

        b_list = vals.copy()
        b_coeffs = clist.copy()

        b_list.pop(idx)
        D_coeff = b_coeffs.pop(idx)

        if D_coeff is None:
            raise ValueError(
                f"Cannot pass None coefficient for diagonal {idx}, "
                "should set whole row to None"
            )

        blbc = [(l, c) for (l, c) in zip(b_list, b_coeffs) if c is not None]

        clean_b_list, clean_c_list = list(zip(*blbc))

        assert len(clean_b_list) == len(clean_c_list)

        match list(clean_b_list):
            case []:
                # The bounded sum is empty, so returns 0 for discount
                D_i = vals[idx]
            case [one_input]:
                D_i = discount_by(vals[idx], one_input)
            case [*_]:
                B_i = bounded_sum(list(clean_b_list), list(clean_c_list))
                D_i = discount_by(vals[idx], B_i)

        return D_i, D_coeff

    D_vec = [d_i_for(idx) for idx in range(len(vals))]

    D_vec_clean = [d for d in D_vec if d is not None]

    if not D_vec_clean:
        raise ValueError("No input rows actually had coefficients")

    D_v, D_c = list(zip(*D_vec_clean))

    return bounded_sum(list(D_v), list(D_c))
