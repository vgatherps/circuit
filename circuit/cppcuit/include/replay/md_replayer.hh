#pragma once

#include <nlohmann/json_fwd.hpp>
#include <string>
#include <unordered_map>
#include <vector>

#include "md_types/trade_message_generated.h"


enum class MdCategory { Trade };

class MarketStreamConfig {
  MdCategory category;
  std::string filename;
  std::string symbol;
};

struct MdSymbology {
  std::unordered_map<std::string, std::size_t> symbol_to_index;
};

struct MdCallbacks {
    std::vector<void(*)(void *, std::uint64_t, const TradeUpdate *)> trade_callbacks;
};