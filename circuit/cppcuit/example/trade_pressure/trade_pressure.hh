#pragma once

#include <optional>

struct PerMarketParams
{
    double book_weight;
    double pricesize_weight;
};

struct RunningImpulseManager
{
    double current_pricesize;
    double current_impulse;
    double deepest_price;
    double score;
};

struct PerMarketInfo
{
    PerMarketParams params;
    std::optional<RunningImpulseManager> buys;
    std::optional<RunningImpulseManager> sells;
};

struct TrueTradePressure
{
};