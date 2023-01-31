#pragma once

#include <cstdint>
#include <nlohmann/json_fwd.hpp>

#include "cppcuit/runtime_error.hh"

#include "cppcuit/signal_requirements.hh"
#include "timer/timer_queue.hh"

// Right now this only takes doubles
// TODO refactor to take a decay source as an input
// instead of managing the timer itself?
class DecayingSum {
  double tick_decay;
  void do_init(const nlohmann::json &json);

public:
  using RunningTickScore = double;
  template <class I, class O>
    requires(HAS_OPT_REF(I, double, tick) &&
             HAS_REF_FIELD(O, double, running_sum))
  void on_tick(I input, O output) {
    if (!input.tick.valid()) {
      return;
    }
    output.running_sum = output.running_sum * this->tick_decay + *input.tick;
  }

  template <class I, class O>
    requires(HAS_OPT_REF(I, double, decay) &&
             HAS_REF_FIELD(O, double, running_sum))
  void decay(I input, O output) {
    // TODO have some idea of always valid inputs?
    // This would basically be like the time metadata?
    if (input.decay.valid()) {
      output.running_sum *= *input.decay;
    } else {
      cold_runtime_error("Decay was impossibly invalid");
    }
  }

  template <class O>
    requires(HAS_REF_FIELD(O, double, running_sum))
  void init(O output, const nlohmann::json &params) {
    output.running_sum = 0.0;
    this->do_init(params);
  }

  DecayingSum() = default;
};