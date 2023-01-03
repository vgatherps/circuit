#include "replay/md_replayer.hh"

#include "io/zlib_streamer.hh"
#include "replay/md_source.hh"

#include <span>
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
                                              TidType tid) {
  Streamer stream{std::make_unique<ZlibReader>(name_for_stream(config, date))};
  stream.fetch_up_to(1024 * 1024);
  switch (config.category) {
  case MdCategory::Depth:
    return std::make_unique<MdStreamReader<DepthMessageConverter, TidType>>(
        std::move(stream), tid);
  case MdCategory::Trade:
    return std::make_unique<MdStreamReader<TradeMessageConverter, TidType>>(
        std::move(stream), tid);
  }
}

TidCollator collator_from_configs(std::span<MarketStreamConfig> configs,
                                  const std::string &date,
                                  MdSymbology &symbology) {
  std::vector<std::unique_ptr<TidSource>> sources;
  for (const MarketStreamConfig &config : configs) {
    TidType tid = symbology.get_tid(config.exchange, config.symbol);
    sources.push_back(source_from_config(config, date, tid));
  }

  return {std::move(sources)};
}

} // namespace

TidType MdSymbology::get_tid(std::string exchange, std::string symbol) {
  ExchangeSymbol exch_sym{exchange, symbol};
  // theoretical overflow risk here
  auto [tid_iter, created] =
      symbol_to_index.insert({exch_sym, (TidType)index_to_symbol.size()});
  if (created) {
    index_to_symbol.push_back(exch_sym);
  }

  return tid_iter->second;
}