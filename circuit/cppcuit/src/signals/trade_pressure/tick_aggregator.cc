#include "signals/trade_pressure/tick_aggregator.hh"
#include "math/fast_exp_64.hh"

#include <iostream>
#include <nlohmann/json.hpp>

namespace {

double score_pricesize(double pricesize, double scale) {
  assert(pricesize >= 0.0);
  assert(scale >= 0.0);

  double exp_ps = FastExpE.compute(pricesize * scale);

  assert(exp_ps <= 1.0);
  assert(exp_ps >= 0.0);

  return 1.0 - exp_ps;
}

double weight_distance_for(double price, double fair, double weight,
                           Side side) {

  double ratio = price / fair;

  double bps_aggressive = flip_sign_if_buy(side, 1.0 - ratio);

  // TODO cap this at something reasonable
  return FastExpE.compute(weight * bps_aggressive);
}

static RunningImpulseManager impulse_from_price(double price, double fair,
                                                double weight, Side side) {
  return {.current_pricesize = 0.0,
          .current_impulse = 0.0,
          .deepest_price = price,
          .distance_score = weight_distance_for(price, fair, weight, side)};
}

static void update_impulse(RunningImpulseManager &m, double price, double size,
                           double pricesize_scale) {

  m.current_pricesize += price * size;
  m.current_impulse = score_pricesize(m.current_pricesize, pricesize_scale);
}

static void update_price(RunningImpulseManager &m, double price, double fair,
                         double dist_weight, Side side) {

  m.deepest_price = deepest(side, price, m.deepest_price);
  // we always ahve to re-weight as the fair changes
  m.distance_score =
      weight_distance_for(m.deepest_price, fair, dist_weight, side);
}
} // namespace

double SingleTickAggregator::handle_trade(const Trade *trade, double fair) {
  bool was_empty = this->running.is_empty();

  Side side = trade->buy() ? Side::Buy : Side::Sell;
  if (was_empty) {
    this->running = impulse_from_price(trade->price(), fair,
                                       this->params.distance_weight, side);
  }

  update_price(this->running, trade->price(), fair,
               this->params.distance_weight, side);
  update_impulse(this->running, trade->price(), trade->size(),
                 this->params.pricesize_weight);

  return this->running.impulse();
}

void SingleTickAggregator::do_init(const nlohmann::json &j) {
  j["pricesize_weight"].get_to(this->params.pricesize_weight);
  j["distance_weight"].get_to(this->params.distance_weight);
}