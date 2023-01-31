#include "signals/trade_pressure/decaying_sum.hh"

#include "cppcuit/runtime_error.hh"

#include <iostream>
#include <nlohmann/json.hpp>

constexpr static double DECAY_THRESHOLD = 1e-6;

void DecayingSum::do_init(const nlohmann::json &json) {
  double tick_decay = json["tick_decay"].get<double>();

  if (tick_decay <= 0.0 || tick_decay > 1.0) {
    cold_runtime_error("Got bogus tick decay");
  }

  this->tick_decay = tick_decay;
}