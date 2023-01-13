#include "replay/md_replayer.hh"

#include "cppcuit/overload.hh"
#include "cppcuit/runtime_error.hh"
#include "io/zlib_streamer.hh"
#include "replay/md_source.hh"

#include <nlohmann/json.hpp>
#include <scelta.hpp>

#include <format>
#include <iostream>
#include <sstream>

using TidSource = CollatorSource<TidMdMessage>;

namespace {

const char *name_from_category(MdCategory category) {
  switch (category) {
  case MdCategory::Depth:
    return "depth";
  case MdCategory::Trade:
    return "trade";
  }

  throw std::runtime_error("Unreachable");
}

std::string name_for_stream(const MarketStreamConfig &config,
                            const std::string &date) {
  std::stringstream stream;
  stream << config.exchange << "_" << name_from_category(config.category) << "_"
         << config.symbol << "_" << date << ".md.gz";
  return stream.str();
}

std::unique_ptr<TidSource> source_from_config(const MarketStreamConfig &config,
                                              const std::string &date,
                                              const std::string &data_dir,
                                              TidType tid) {
  std::string stream_file_name = name_for_stream(config, date);
  Streamer stream{std::make_unique<ZlibReader>(data_dir + stream_file_name)};
  stream.fetch_up_to(1024 * 1024);
  switch (config.category) {
  case MdCategory::Depth:
    return std::make_unique<MdStreamReader<DepthMessageConverter, TidType>>(
        std::move(stream), tid);
  case MdCategory::Trade:
    return std::make_unique<MdStreamReader<SingleTradeConverter, TidType>>(
        std::move(stream), tid);
  }

  throw std::runtime_error("Unreachable");
}

} // namespace

TidCollator collator_from_configs(std::span<MarketStreamConfig> configs,
                                  const std::string &date,
                                  const std::string &data_dir,
                                  MdSymbology &symbology) {
  std::vector<std::unique_ptr<TidSource>> sources;
  for (const MarketStreamConfig &config : configs) {
    TidType tid = symbology.get_tid(config.exchange, config.symbol);
    sources.push_back(source_from_config(config, date, data_dir, tid));
  }

  return {std::move(sources)};
}

TidType MdSymbology::get_tid(std::string exchange, std::string symbol) {
  ExchangeSymbol exch_sym{exchange, symbol};
  // theoretical overflow risk here
  TidType tid = index_to_symbol.size();
  auto [tid_iter, created] = symbol_to_index.insert({exch_sym, tid});
  if (created) {
    index_to_symbol.push_back(exch_sym);
  }

  return tid_iter->second;
}

template <class T> void wrong_call(WrongCallbackType w) {
  throw std::runtime_error(std::string("Expected type ") + typeid(T).name() +
                           "got typeid " + w.type.name());
}

template <class T> auto matcher(CircuitCall<T> &dest) {
  // Not entirely sure why I need to wrap wrong call in a lambda
  return scelta::match([&](CircuitCall<T> value) { dest = value; },
                       [&](NoCallbackFound) { dest = nullptr; },
                       [](WrongCallbackType w) { wrong_call<T>(w); });
};

MdCallbacks::MdCallbacks(MdSymbology syms, Circuit *circuit)
    : symbology(syms), callbacks(syms.n_symbols()), circuit(circuit) {
  for (const auto &[symbol_exchange, tid] : syms.symbols()) {

    const auto &[exchange, symbol] = symbol_exchange;
    std::string single_trade_name = symbol + "_" + exchange + "_trades";
    std::string single_diff_name = symbol + "_" + exchange + "_diffs";

    matcher(callbacks[tid].single_trade)(
        circuit->load_callback<TradeInput>(single_trade_name));
    matcher(callbacks[tid].diff)(
        circuit->load_callback<DiffInput>(single_diff_name));
  }
}

void MdCallbacks::handle_update(TidMdMessage msg) const {
  const SymbolCallbacks &callbacks = this->callbacks[msg.key];

  auto caller = [&]<class I>(CircuitCall<I> call) {
    using T = typename I::InType;
    return [&, call = call](const T *p) {
      if (call == nullptr) {
        cold_runtime_error("Streamer got message it had no callback for");
      }
      call(this->circuit, msg.local_timestamp_ns, I(p), {});
    };
  };

  scelta::match(caller(callbacks.single_trade),
                caller(callbacks.diff))(msg.update);
}

void MdCallbacks::replay_all(TidCollator &collator) {
  auto matcher = scelta::match(
      [this](TidMdMessage msg) {
        while (
            this->circuit->examine_timer_queue<false>(msg.local_timestamp_ns)) {
        }
        this->handle_update(msg);
        return true;
      },
      [](scelta::nullopt_t) { return false; });
  while (matcher(collator.next_element())) {
  }
}

MarketStreamConfig from_config(const nlohmann::json &j) {
  std::string str_category = j["category"];

  MdCategory cat;

  if (str_category == "single_trades") {
    cat = MdCategory::Trade;
  } else if (str_category == "depth") {
    cat = MdCategory::Depth;
  } else {
    throw std::runtime_error("Unrecognized md category " + str_category);
  }

  return MarketStreamConfig{
      .category = cat, .exchange = j["exchange"], .symbol = j["symbol"]};
}

MdConfig::MdConfig(const nlohmann::json &config) {
  this->date = config["date"];
  std::vector<nlohmann::json> streams = config["streams"];

  for (nlohmann::json config : streams) {
    this->streams.push_back(from_config(config));
  }
}