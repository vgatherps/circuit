#include "io/zlib_streamer.hh"
#include "md_types/trade_message_generated.h"

#include <flatbuffers/minireflect.h>

#include <iostream>
int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "Don't have a file passed" << std::endl;
    return -1;
  }
  std::cout << "Reading trades file " << argv[1] << std::endl;

  std::unique_ptr<ByteReader> zlib_reader =
      std::make_unique<ZlibReader>(argv[1]);

  Streamer streamer(std::move(zlib_reader));

  streamer.fetch_up_to(1024 * 1024);

  while (streamer.available() > 0) {
    streamer.ensure_available(4);
    const char *length_data = streamer.data();
    std::uint32_t length;
    static_assert(sizeof(length) == 4);
    memcpy(&length, length_data, sizeof(length));
    streamer.commit(sizeof(length));

    streamer.ensure_available(length);
    const char *trade_message_data = streamer.data();

    const TradeMessage *trade = GetTradeMessage(trade_message_data);

    streamer.commit(length);
  }

  return 0;
}