#pragma once

#include "cppcuit/packed_optional.hh"
#include "md_types/trade_message_generated.h"

struct TradeInput {
    Optionally<const TradeUpdate *>::Optional trades;
};