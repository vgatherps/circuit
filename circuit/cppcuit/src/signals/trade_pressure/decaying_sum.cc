#include "signals/trade_pressure/decaying_sum.hh"

#include <iostream>
#include <nlohmann/json.hpp>

constexpr static double DECAY_THRESHOLD = 1e-6;

// Don't inline into the decay timer to preserve icache
double __attribute__((noinline))
DecayingSum::compute_decay(std::uint64_t now, double current_sum,
                           TimerHandle reschedule) {
  if (now <= this->last_decay) {
    return current_sum;
  }

  double diff = now - this->last_decay;

  double half_lives = diff * this->inv_half_life_ns;

  double decay_by = FastExp2.compute(half_lives);

  this->last_decay = now;

  double new_sum = current_sum * decay_by;
  if (!this->has_timer_scheduled && std::abs(new_sum) > DECAY_THRESHOLD) {
    has_timer_scheduled = true;
    reschedule.schedule_call_at(now + this->reschedule_decay_timer);
  }
  return new_sum;
}

void DecayingSum::do_init(const nlohmann::json &json) {
  double half_life_ns = json["half_life_ns"].get<double>();
  double tick_decay = json["tick_decay"].get<double>();

  // anything less than this is almost certainly an error
  if (half_life_ns <= 10000.0) {
    // todo format in C++
    cold_runtime_error("Got bogus half life for decaying sum");
  }

  if (tick_decay <= 0.0 || tick_decay > 1.0) {
    cold_runtime_error("Got bogus tick decay");
  }

  this->inv_half_life_ns = 1.0 / half_life_ns;
  this->tick_decay = tick_decay;

  this->last_decay = 0;
  this->reschedule_decay_timer = half_life_ns / 20;
}