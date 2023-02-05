from typing import List
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.minmax import max_of, min_of
from pycircuit.circuit_builder.signals.select import select
from pycircuit.circuit_builder.circuit_context import CircuitContextManager

# Taken a value A, discount by value B towards zero (but never past)
# Essentially, if value A is positive and value B is positive, return max(0, A-B)
# If both are negative, return min(0, A-B)
# Otherwise do nothing
# a < 0 | b < 0 |
#   0   |   0   | max(0, A - B)
#   0   |   1   | A
#   1   |   0   | A
#   1   |   1   | min(0, A - B)
# also equal to
# a < 0 => max(A, min(0, A-B))
# a > 0 => min(A, max(0, A-B))
# or
# a < 0 => A - max(A, min(B, 0))
# a > 0 => A - min(A, max(B, 0)))
# This has slightly more computation,
# but has fewer and more predictable branches
def discount_by(a: HasOutput, b: HasOutput, zero_type="double"):

    context = CircuitContextManager.active_circuit()

    zero = context.make_constant(zero_type, constructor="0")

    a_leq_zero_case = max_of(a, min_of(b, zero))
    a_geq_zero_case = min_of(a, max_of(b, zero))

    subtractor = select(a_leq_zero_case, a_geq_zero_case, a <= zero)

    return a - subtractor
