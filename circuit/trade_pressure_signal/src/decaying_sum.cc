#include "decaying_sum.hh"

#include <nlohmann/json.hpp>
#include <stdexcept>
// Don't inline into the decay timer to preserve icache
double __attribute__((noinline))
DecayingSum::compute_decay(std::uint64_t now, double current_sum) {
  if (now <= this->last_decay) {
    return current_sum;
  }

  double diff = now - this->last_decay;

  double half_lives = diff * this->inv_half_life_ns;

  double decay_by = FastExp2.compute(half_lives);

  this->last_decay = now;

  return current_sum * decay_by;
}

double DecayingSum::compute_and_schedule_decay(std::uint64_t now,
                                               double current_sum,
                                               TimerHandle reschedule) {
  reschedule.schedule_call_at(now + this->reschedule_decay_timer);
  return this->compute_decay(now, current_sum);
}

void DecayingSum::do_init(TimerHandle timer, const nlohmann::json &json) {
  double half_life_ns = json["half_life_ns"].get<double>();
  double tick_decay = json["tick_decay"].get<double>();

  // anything less than this is almost certainly an error
  if (half_life_ns <= 10000.0) {
    // todo format in C++
    throw std::runtime_error("Got bogus half life for decaying sum");
  }

  if (tick_decay <= 0.0 || tick_decay > 1.0) {
    throw std::runtime_error("Got bogus tick decay");
  }

  this->inv_half_life_ns = 1.0 / half_life_ns;
  this->tick_decay = tick_decay;

  this->last_decay = 0;
  this->reschedule_decay_timer = half_life_ns / 20;

  // This will automatically get called at the start and reschedule from now
  timer.schedule_call_at(0);
}