#pragma once

#include "cppcuit/packed_optional.hh"
#include "md_types/common_generated.h"

struct TradeInput {
    Optionally<const Trade *>::Optional trade;
};

struct DiffInput {
    Optionally<const DepthUpdate *>::Optional depth;
};