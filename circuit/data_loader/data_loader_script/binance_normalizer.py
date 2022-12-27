from typing import Any, Dict
from .fbgen.Trade import CreateTrade
from .fbgen.SingleTradeMessage import (
    SingleTradeMessageStart,
    SingleTradeMessageEnd,
    SingleTradeMessageAddLocalTimeUs,
    SingleTradeMessageAddMessage,
)


def binance_trade_normalizer(builder, local_time_us: int, in_json: Dict[str, Any]):
    data = in_json["data"]
    exchange_timestamp_us = 1000 * data["T"]
    price = float(data["p"])
    size = float(data["q"])
    buy = not data["m"]

    trade = CreateTrade(builder, price, size, exchange_timestamp_us, buy)

    SingleTradeMessageStart(builder)

    SingleTradeMessageAddMessage(builder, trade)
    SingleTradeMessageAddLocalTimeUs(builder, local_time_us)
    update = SingleTradeMessageEnd(builder)
    builder.Finish(update)
