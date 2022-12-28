#pragma once

#include <nlohmann/json_fwd.hpp>
#include <string>
#include <unordered_map>
#include <vector>

#include "md_types/trade_message_generated.h"
#include "md_inputs.hh"


enum class MdCategory { Trade };

class MarketStreamConfig {
  MdCategory category;
  std::string filename;
  std::string symbol;
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