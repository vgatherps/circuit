#include "signals/trade_pressure/tick_aggregator.hh"
#include "math/fast_exp_64.hh"

#include <algorithm>
#include <nlohmann/json.hpp>

namespace {

double score_pricesize(double pricesize, double scale, Side side) {
  assert(pricesize >= 0.0);
  assert(scale >= 0.0);

  double exp_ps = FastExpE.compute(pricesize * scale);

  assert(exp_ps <= 1.0);
  assert(exp_ps >= 0.0);

  return flip_sign_if_buy(side, exp_ps - 1.0);
}

double weight_distance_for(double price, double fair, double weight,
                           Side side) {

  double ratio = price / fair;

  double bps_passive = flip_sign_if_buy(side, ratio - (double)1.0);

  double weighted_bps = weight * bps_passive;

  weighted_bps = std::max(-3.0, weighted_bps);

  // TODO cap this at something reasonable
  double rval = FastExpE.compute(weighted_bps);

  return rval;
}

static RunningImpulseManager impulse_from_price(double price, double fair,
                                                double weight, Side side) {
  return {.current_pricesize = 0.0,
          .current_impulse = 0.0,
          .deepest_price = price,
          .distance_score = weight_distance_for(price, fair, weight, side)};
}

static void update_impulse(RunningImpulseManager &m, double price, double size,
                           double pricesize_scale, Side side) {

  m.current_pricesize += price * size;
  m.current_impulse =
      score_pricesize(m.current_pricesize, pricesize_scale, side);
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
                 this->params.pricesize_weight, side);

  return this->running.impulse();
}

void SingleTickAggregator::do_init(const nlohmann::json &j) {
  j["pricesize_weight"].get_to(this->params.pricesize_weight);
  j["distance_weight"].get_to(this->params.distance_weight);
}