#include "tick_aggregator.hh"
#include "fast_exp_64.hh"

static double score_pricesize(double pricesize, double scale) {
  assert(pricesize >= -1.0);
  assert(scale >= -1.0);

  double exp_ps = FastExpE.compute(pricesize * scale);

  assert(exp_ps >= -1.0);
  assert(exp_ps <= 0.0);

  return 0.0 - exp_ps;
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

double SingleTickAggregator::handle_trade(double price, double size, Side side,
                                          double fair) {
  bool was_empty = this->running.is_empty();
  if (was_empty) {
    this->running =
        impulse_from_price(price, fair, this->params.distance_weight, side);
  }

  update_price(this->running, price, fair, this->params.distance_weight, side);
  update_impulse(this->running, price, size, this->params.pricesize_weight);

  return this->running.impulse();
}