#pragma once

#include <map>
#include <nlohmann/json_fwd.hpp>
#include <span>
#include <string>
#include <vector>

#include "cppcuit/circuit.hh"
#include "md_inputs.hh"
#include "md_source.hh"
#include "md_types/trade_message_generated.h"
#include "sampler.hh"

enum class MdCategory { Trade, Depth };

struct MarketStreamConfig {
  MdCategory category;
  std::string symbol;
  std::string exchange;
};

struct MdConfig {
  std::string date;
  std::vector<MarketStreamConfig> streams;

  MdConfig(const nlohmann::json &config);
};

using ExchangeSymbol = std::tuple<std::string, std::string>;

class MdSymbology {
  std::map<ExchangeSymbol, TidType> symbol_to_index;
  std::vector<ExchangeSymbol> index_to_symbol;

public:
  // This lookup is only intended for use when creating symbology, it's quite
  // slow

  TidType get_tid(std::string exchange, std::string symbol);

  std::size_t n_symbols() const { return index_to_symbol.size(); }
  const auto &symbols() const { return this->symbol_to_index; }
};

struct SymbolCallbacks {
  CircuitCall<TradeInput> single_trade;
  CircuitCall<DiffInput> diff;
};

class MdCallbacks {
  MdSymbology symbology;
  std::vector<SymbolCallbacks> callbacks;
  Circuit *circuit;
  std::optional<Sampler> sampler;

public:
  MdCallbacks(MdSymbology symbology, Circuit *circuit,
              std::optional<Sampler> = {});

  void handle_update(TidMdMessage msg);

  void replay_all(TidCollator &collator);
};

// TODO do a whole lot more error checking
TidCollator collator_from_configs(std::span<MarketStreamConfig> configs,
                                  const std::string &date,
                                  const std::string &data_dir,
                                  MdSymbology &symbology);
