import asyncio
from tardis_client import TardisClient, Channel
from datetime import date, timedelta
from .binance_normalizer import binance_trade_normalizer
import flatbuffers
import gzip

from .fbgen.MdMessage import MdMessage


async def replay(exchange: str, date: date, channel: Channel):
    file = gzip.open("trades_buf.gz", "wb")
    tardis_client = TardisClient()

    start = date.strftime("%Y-%m-%d")
    end = (date + timedelta(days=1)).strftime("%Y-%m-%d")

    # replay method returns Async Generator
    # https://rickyhan.com/jekyll/update/2018/01/27/python36.html
    messages = tardis_client.replay(
        exchange=exchange,
        from_date=start,
        to_date=end,
        filters=[channel],
    )

    # this will print all trades and orderBookL2 messages for XBTUSD
    # and all trades for ETHUSD for bitmex exchange
    # between 2019-06-01T00:00:00.000Z and 2019-06-02T00:00:00.000Z (whole first day of June 2019)
    running_buffer = bytearray()
    async for local_timestamp, message in messages:
        # local timestamp is a Python datetime that marks timestamp when given message has been received
        # message is a message object as provided by exchange real-time stream
        builder = flatbuffers.Builder(1024)
        binance_trade_normalizer(
            builder, int(local_timestamp.timestamp() * 1e6), message
        )
        output = builder.Output()

        output_len = len(output)
        running_buffer.extend(output_len.to_bytes(4, "little"))
        running_buffer.extend(output)

        if len(running_buffer) > 1000000:
            file.write(running_buffer)
            running_buffer.clear()

    if len(running_buffer) > 0:
        file.write(running_buffer)
        running_buffer.clear()


asyncio.run(
    replay(
        "binance-futures",
        date=date(year=2022, month=1, day=1),
        channel=Channel(name="trade", symbols=["btcusdt"]),
    )
)
