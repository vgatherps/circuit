from typing import Sequence
from pycircuit.circuit_builder.component import HasOutput, Component
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.circuit import OutputArray
from ..running_name import get_novel_name
from ..bbo import bbo_ask_price, bbo_bid_price
from ..minmax import min_of, max_of
from .ewma_of import ewma_of


def sided_bbo_returns(
    bbo: HasOutput, decay_sources: HasOutput | Sequence[HasOutput]
) -> Component:
    """
    Sums the negative returns of bid with the positive returns of ask.

    on a price move up, ask tends to move before bid (and vice-versa on move down)

    The mid will show muted moves in each direction when this happens
    but won't show muted returns when both move together
    (i.e. liquidity is placed and taken) in same update

    This however would give the same returns in each case
    """
    bid_price = bbo_bid_price(bbo)
    ask_price = bbo_ask_price(bbo)
    bid_ewma = ewma_of(bid_price, decay_sources)
    ask_ewma = ewma_of(ask_price, decay_sources)

    negative_bid_returns = (bid_price - max_of(bid_ewma, bid_price)) / bid_price

    # Likewise only take positive ask returns - when ewma is below ask
    positive_ask_returns = (ask_price - min_of(ask_ewma, ask_price)) / ask_price

    return negative_bid_returns + positive_ask_returns
