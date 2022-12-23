from typing import Any, Dict
from .fbgen.RawMdMessage import RawMdMessage
from .fbgen.Trade import Trade, CreateTrade
from .fbgen.TradeUpdate import (
    TradeUpdateStartTradesVector,
    TradeUpdateStart,
    TradeUpdateEnd,
    TradeUpdateAddTrades,
)
from .fbgen.TradeMessage import (
    TradeMessageAddMessage,
    TradeMessageStart,
    TradeMessageEnd,
    TradeMessageAddLocalTimeUs,
)


def binance_trade_normalizer(builder, local_time_us: int, in_json: Dict[str, Any]):
    data = in_json["data"]
    exchange_timestamp_us = 1000 * data["T"]
    price = float(data["p"])
    size = float(data["q"])
    buy = not data["m"]

    TradeUpdateStartTradesVector(builder, 1)
    CreateTrade(builder, price, size, exchange_timestamp_us, buy)
    trades = builder.EndVector()

    TradeUpdateStart(builder)
    TradeUpdateAddTrades(builder, trades)
    trade_update = TradeUpdateEnd(builder)

    TradeMessageStart(builder)

    TradeMessageAddMessage(builder, trade_update)
    TradeMessageAddLocalTimeUs(builder, local_time_us)
    update = TradeMessageEnd(builder)
    builder.Finish(update)
