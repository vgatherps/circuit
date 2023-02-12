from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.component import HasOutput
from pycircuit.circuit_builder.component import Component
from pycircuit.circuit_builder.signals.constant import make_double

from pycircuit.circuit_builder.signals.tree_sum import tree_sum
from ..tree_sum import tree_sum
from ..unary_arithmetic import cexp, csqrt, clog, cabs

MAKE_RETURNS_MORE_NORMAL_MULT = 10000


def make_static_book_fair(
    aggregated: Component, mid: HasOutput, levels: int, prefix: str
):
    circuit = CircuitContextManager.active_circuit()
    bid_prices = aggregated.output("bid_prices")
    bid_sizes = aggregated.output("bid_sizes")
    ask_prices = aggregated.output("ask_prices")
    ask_sizes = aggregated.output("ask_sizes")

    fix_returns_mult = make_double(MAKE_RETURNS_MORE_NORMAL_MULT)

    scale = circuit.make_parameter(f"{prefix}_scale")
    scale = cabs(scale)

    bid_scores = []
    ask_scores = []

    for i in range(levels):
        adjusted_bid_distance = fix_returns_mult * ((bid_prices[i] - mid) / mid)
        adjusted_ask_distance = fix_returns_mult * ((ask_prices[i] - mid) / mid)

        bid_weight = cexp(adjusted_bid_distance * scale)
        ask_weight = cexp(adjusted_ask_distance * scale)

        bid_score = csqrt(bid_sizes[i])
        ask_score = csqrt(ask_sizes[i])

        bid_scores.append(bid_score * bid_weight)
        ask_scores.append(ask_score * ask_weight)

    total_bid_score = tree_sum(bid_scores)
    total_ask_score = tree_sum(ask_scores)

    # Here, trying to ensure that interactions with the 10k multiplier always happen
    # before scaling in the autodiff graph
    # otherwise it's really hard to propagate gradients properly

    # I suspect this works poorly for low price coins? These tricks are needed to keep scale
    # in a respectable range (i.e. not being equal to 1e-5)

    log_ratio = clog(total_bid_score / total_ask_score)

    adjusted_fair = log_ratio / (make_double(2.0) * scale)

    unadjust_mult = mid / fix_returns_mult

    return (adjusted_fair + make_double(1.0)) * unadjust_mult
