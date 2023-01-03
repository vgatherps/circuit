#pragma once

#include <nlohmann/json_fwd.hpp>
#include <string>
#include <unordered_map>
#include <vector>

#include "md_inputs.hh"
#include "md_types/trade_message_generated.h"

enum class MdCategory { Trade, Depth };

struct MarketStreamConfig {
  MdCategory category;
  std::string symbol;
  std::string exchange;
};

struct MdSymbology {
  std::unordered_map<std::string, std::size_t> symbol_to_index;
};

struct SymbolCallbacks {
  void (*single_trade)(void *, std::uint64_t, TradeInput);
  void (*diff)(void *, std::uint64_t, DiffInput);
};

struct MdCallbacks {
  MdSymbology symbology;
  std::vector<SymbolCallbacks> callbacks;
};