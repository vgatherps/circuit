#pragma once

#include "cppcuit/packed_optional.hh"
#include "md_types/common_generated.h"

struct TradeInput {
    Optionally<const Trade *>::Optional trade;
    TradeInput(const Trade *p) : trade(p) {}

    using InType = Trade;
};

struct DiffInput {
    Optionally<const DepthUpdate *>::Optional depth;
    DiffInput(const DepthUpdate *p) : depth(p) {}

    using InType = DepthUpdate;
};