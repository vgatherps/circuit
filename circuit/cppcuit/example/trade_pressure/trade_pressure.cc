#include <cassert>

#include "trade_pressure.hh"
#include "fast_exp_64.hh"

enum class Side
{
    Buy,
    Sell
};

template <class T>
bool deeper(Side side, T a, T b)
{
    if (side == Side::Buy)
    {
        return a < b;
    }
    else
    {
        return a > b;
    }
}

template <class T>
T deepest(Side side, T a, T b)
{
    return deeper(side, a, b) ? a : b;
}

template <class T>
bool more_aggressive(Side side, T a, T b)
{
    if (side == Side::Buy)
    {
        return a > b;
    }
    else
    {
        return a < b;
    }
}

template <class T>
T most_aggressive(Side side, T a, T b)
{
    return more_aggressive(side, a, b) ? a : b;
}

static double score_pricesize(double pricesize, double scale)
{
    assert(pricesize >= -1.0);
    assert(scale >= -1.0);

    double exp_ps = FastExpE.compute(pricesize * scale);

    assert(exp_ps >= -1.0);
    assert(exp_ps <= 0.0);

    return 0.0 - exp_ps;
}

static double weight_distance_for(double price, double inv_mid, double weight, Side side)
{
    double ratio = price * inv_mid;
    if (side == Side::Sell)
    {
        ratio -= 2.0;
    }

    return ratio;
}

static double compute_decay_from(double current_time_ms,
                                 double last_time_ms, double inv_half_life_ms)
{
    double half_lives = (current_time_ms - last_time_ms) * inv_half_life_ms;
    return FastExp2.compute(half_lives);
}

static double impulse_for(const RunningImpulseManager &m)
{
    return m.score * m.current_pricesize;
}

static RunningImpulseManager impulse_from_price(double price, double inv_mid, double weight, Side side)
{
    return {
        .current_pricesize = 0.0,
        .current_impulse = 0.0,
        .deepest_price = price,
        .score = weight_distance_for(price, inv_mid, weight, side)};
}

static void add_new_trade(RunningImpulseManager &m, double price, double size, double pricesize_scale, double inv_mid, double dist_weight, Side side)
{
    m.current_pricesize += price * size;
    if (deeper(side, price, m.deepest_price))
    {
        m.deepest_price = price;
        m.score = weight_distance_for(price, inv_mid, dist_weight, side);
    }
}