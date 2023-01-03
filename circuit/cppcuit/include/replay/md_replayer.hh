#pragma once

#include <map>
#include <nlohmann/json_fwd.hpp>
#include <string>
#include <vector>

#include "md_inputs.hh"
#include "md_source.hh"
#include "md_types/trade_message_generated.h"

enum class MdCategory { Trade, Depth };

struct MarketStreamConfig {
  MdCategory category;
  std::string symbol;
  std::string exchange;
};

using ExchangeSymbol = std::tuple<std::string, std::string>;

class MdSymbology {
  std::map<ExchangeSymbol, TidType> symbol_to_index;
  std::vector<ExchangeSymbol> index_to_symbol;

public:
  // This lookup is only intended for use when creating symbology, it's quite
  // slow

  TidType get_tid(std::string exchange, std::string symbol);
};

struct SymbolCallbacks {
  void (*single_trade)(void *, std::uint64_t, TradeInput);
  void (*diff)(void *, std::uint64_t, DiffInput);
};

struct MdCallbacks {
  MdSymbology symbology;
  std::vector<SymbolCallbacks> callbacks;
};