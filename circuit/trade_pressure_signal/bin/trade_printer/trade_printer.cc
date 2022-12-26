#include "io/zlib_streamer.hh"
#include "md_types/trade_message_generated.h"
#include "trade_pressure/pressure.hh"

#include <flatbuffers/minireflect.h>
#include <nlohmann/json.hpp>

#include <iostream>

using nlohmann::literals::operator"" _json;

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

  TradePressure pressure_circuit(R"lit(
  {
    "SPY_decaying_tick_sum": {
      "half_life_ns": 1000000,
      "tick_decay": 0.99
    },
    "GOOG_decaying_tick_sum": {
      "half_life_ns": 1000000,
      "tick_decay": 0.99
    },
    "MSFT_decaying_tick_sum": {
      "half_life_ns": 1000000,
      "tick_decay": 0.99
    },
    "SPY_BATS_tick_aggregator": {},
    "SPY_NASDAQ_tick_aggregator": {},
    "SPY_NYSE_tick_aggregator": {},
    "GOOG_BATS_tick_aggregator": {},
    "GOOG_NASDAQ_tick_aggregator": {},
    "GOOG_NYSE_tick_aggregator": {},
    "MSFT_BATS_tick_aggregator": {},
    "MSFT_NASDAQ_tick_aggregator": {},
    "MSFT_NYSE_tick_aggregator": {}
  }
  )lit"_json);

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

    const flatbuffers::Vector<const Trade *> &trade_vec =
        *trade->message()->trades();

    std::uint64_t local_time_ns = 1000 * trade->local_time_us();

    while (pressure_circuit.examine_timer_queue<false>(local_time_ns)) {
    }

    TradeInput input{.trades = trade->message()};

    pressure_circuit.GOOG_BATS_trades(local_time_ns, input, {});

    streamer.commit(length);
  }

  return 0;
}