#include "signals/decay/decay_source.hh"

#include "cppcuit/runtime_error.hh"
#include "math/fast_exp_64.hh"

#include <iostream>
#include <nlohmann/json.hpp>

constexpr static double DECAY_THRESHOLD = 1e-6;

double DecaySource::compute_decay(std::uint64_t now, TimerHandle reschedule) {
  if (now <= this->last_decay) {
    return 1.0;
  }

  double diff = now - this->last_decay;

  double half_lives = diff * this->inv_half_life_ns;

  double decay_by = FastExp2.compute_out_of_line(half_lives);

  this->last_decay = now;

  reschedule.schedule_call_at(now + this->reschedule_decay_timer);

  return decay_by;
}

void DecaySource::do_init(TimerHandle timer, const nlohmann::json &json) {
  double half_life_ns = json["half_life_ns"].get<double>();

  // anything less than this is almost certainly an error
  if (half_life_ns <= 10000.0) {
    // todo format in C++
    cold_runtime_error("Got bogus half life for decaying sum");
  }

  this->inv_half_life_ns = 1.0 / half_life_ns;

  this->last_decay = 0;
  this->reschedule_decay_timer = half_life_ns / 20;

  timer.schedule_call_at(0);
}