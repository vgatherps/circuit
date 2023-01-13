import os
import asyncio
from dataclasses import dataclass
import sys
from typing import Callable, Optional
from argparse_dataclass import ArgumentParser
import dateutil.parser
from tardis_client import TardisClient, Channel
from datetime import date, datetime, timedelta
from .binance_normalizer import binance_trade_normalizer, binance_depth_normalizer
import flatbuffers
import gzip

from .fbgen.MdMessage import MdMessage


@dataclass
class DumpArgs:
    exchange: str
    message_type: str
    symbol: str
    date: str
    out_dir: str = "./"
    tardis_api_key: Optional[str] = None


@dataclass
class Normalizer:
    callback: Callable[[flatbuffers.Builder, int, str], None]
    exchange: str
    channel: Channel


NORMALIZERS = {
    ("binance-futures", "trade"): binance_trade_normalizer,
    ("binance-futures", "depth"): binance_depth_normalizer,
}


async def replay(
    exchange: str,
    channel: str,
    symbol: str,
    date: date,
    out_dir: str,
    api_key: Optional[str],
):

    callback = NORMALIZERS[(exchange, channel)]
    tardis_channel = Channel(name=channel, symbols=[symbol])
    filename = f"{exchange}_{channel}_{symbol}_{date}.md.gz".replace("-", "_")
    filepath = os.path.join(out_dir, filename)
    file = gzip.open(filepath, "wb")
    tardis_client = TardisClient(api_key=api_key)

    start = date.strftime("%Y-%m-%d")
    end = (date + timedelta(days=1)).strftime("%Y-%m-%d")

    # replay method returns Async Generator
    # https://rickyhan.com/jekyll/update/2018/01/27/python36.html
    messages = tardis_client.replay(
        exchange=exchange,
        from_date=start,
        to_date=end,
        filters=[tardis_channel],
    )

    # this will print all trades and orderBookL2 messages for XBTUSD
    # and all trades for ETHUSD for bitmex exchange
    # between 2019-06-01T00:00:00.000Z and 2019-06-02T00:00:00.000Z (whole first day of June 2019)
    running_buffer = bytearray()
    async for local_timestamp, message in messages:
        # local timestamp is a Python datetime that marks timestamp when given message has been received
        # message is a message object as provided by exchange real-time stream
        builder = flatbuffers.Builder(1024)
        callback(builder, int(local_timestamp.timestamp() * 1e6), message)
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


async def main():
    args: DumpArgs = ArgumentParser(DumpArgs).parse_args(sys.argv[1:])

    date: datetime
    date = dateutil.parser.parse(args.date)
    await replay(
        args.exchange,
        args.message_type,
        args.symbol,
        date.date(),
        args.out_dir,
        args.tardis_api_key,
    )


if __name__ == "__main__":
    asyncio.run(main())
