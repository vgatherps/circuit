from typing import Any, Dict
from .fbgen.RawMdMessage import RawMdMessage
from .fbgen.MdMessage import (
    MdMessage,
    MdMessageStart,
    MdMessageEnd,
    MdMessageAddMessageType,
    MdMessageAddMessage,
    MdMessageAddLocalTimeUs,
)
from .fbgen.Trade import Trade, CreateTrade
from .fbgen.TradeUpdate import (
    TradeUpdateStartTradesVector,
    TradeUpdateStart,
    TradeUpdateEnd,
    TradeUpdateAddTrades,
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

    MdMessageStart(builder)

    MdMessageAddMessageType(builder, RawMdMessage.trades)
    MdMessageAddMessage(builder, trade_update)
    MdMessageAddLocalTimeUs(builder, local_time_us)
    update = MdMessageEnd(builder)
    builder.Finish(update)
