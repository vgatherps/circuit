from typing import Any, Dict
from .fbgen.Trade import CreateTrade
from .fbgen.SingleTradeMessage import (
    SingleTradeMessageStart,
    SingleTradeMessageEnd,
    SingleTradeMessageAddLocalTimeUs,
    SingleTradeMessageAddMessage,
)
from .fbgen.DepthUpdate import (
    DepthUpdate,
    DepthUpdateAddAsks,
    DepthUpdateAddBids,
    DepthUpdateAddExchangeTimeUs,
    DepthUpdateEnd,
    DepthUpdateStart,
    DepthUpdateStartAsksVector,
    DepthUpdateStartBidsVector,
)
from .fbgen.Level import CreateLevel
from .fbgen.DepthMessage import (
    DepthMessageAddLocalTimeUs,
    DepthMessageAddMessage,
    DepthMessageEnd,
    DepthMessageStart,
)


def binance_trade_normalizer(builder, local_time_us: int, in_json: Dict[str, Any]):
    data = in_json["data"]
    exchange_timestamp_us = 1000 * data["T"]
    price = float(data["p"])
    size = float(data["q"])
    buy = not data["m"]

    trade = CreateTrade(builder, price, size, int(exchange_timestamp_us), buy)

    SingleTradeMessageStart(builder)

    SingleTradeMessageAddMessage(builder, trade)
    SingleTradeMessageAddLocalTimeUs(builder, local_time_us)
    update = SingleTradeMessageEnd(builder)
    builder.Finish(update)


def binance_depth_normalizer(builder, local_time_us: int, in_json: Dict[str, Any]):
    data = in_json["data"]
    exchange_timestamp_us = 1000 * data["T"]

    asks = data["a"]
    bids = data["b"]

    DepthUpdateStartAsksVector(builder, len(asks))
    for (ask_price, ask_size) in asks:
        CreateLevel(builder, float(ask_price), float(ask_size))
    ask_vec = builder.EndVector()

    DepthUpdateStartBidsVector(builder, len(bids))
    for (bid_price, bid_size) in bids:
        CreateLevel(builder, float(bid_price), float(bid_size))
    bid_vec = builder.EndVector()

    DepthUpdateStart(builder)
    DepthUpdateAddAsks(builder, ask_vec)
    DepthUpdateAddBids(builder, bid_vec)
    DepthUpdateAddExchangeTimeUs(builder, int(exchange_timestamp_us))
    depth = DepthUpdateEnd(builder)

    DepthMessageStart(builder)
    DepthMessageAddMessage(builder, depth)
    DepthMessageAddLocalTimeUs(builder, local_time_us)
    message = DepthMessageEnd(builder)
    builder.Finish(message)
