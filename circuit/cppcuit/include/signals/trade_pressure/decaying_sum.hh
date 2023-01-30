#pragma once

#include <cstdint>
#include <nlohmann/json_fwd.hpp>

#include "cppcuit/signal_requirements.hh"
#include "math/fast_exp_64.hh"
#include "timer/timer_queue.hh"

// Right now this only takes doubles
// TODO refactor to take a decay source as an input
// instead of managing the timer itself?
class DecayingSum {
  double tick_decay;
  double inv_half_life_ns;
  std::uint64_t reschedule_decay_timer;
  std::uint64_t last_decay;
  bool has_timer_scheduled;

  double compute_decay(std::uint64_t now, double current_sum,
                       TimerHandle reschedule);
  void do_init(const nlohmann::json &json);

public:
  using RunningTickScore = double;
  template <class I, class O, class M>
    requires(HAS_OPT_REF(I, double, tick) &&
             HAS_REF_FIELD(O, double, running_sum) &&
             HAS_FIELD(M, TimerHandle, timer) &&
             HAS_FIELD(M, CircuitTime, time))
  void on_tick(I input, O output, M metadata) {
    if (!input.tick.valid()) {
      return;
    }

    double decayed_sum =
        this->compute_decay(metadata.time, output.running_sum, metadata.timer);
    output.running_sum = decayed_sum * this->tick_decay + *input.tick;
  }

  template <class O, class M>
    requires(HAS_REF_FIELD(O, double, running_sum) &&
             HAS_FIELD(M, TimerHandle, timer) &&
             HAS_FIELD(M, CircuitTime, time))
  void decay(O output, M metadata) {
    has_timer_scheduled = false;
    double decayed_sum =
        this->compute_decay(metadata.time, output.running_sum, metadata.timer);

    output.running_sum = decayed_sum;
  }

  template <class O>
    requires(HAS_REF_FIELD(O, double, running_sum))
  void init(O output, const nlohmann::json &params) {
    output.running_sum = 0.0;
    this->do_init(params);
  }

  DecayingSum() = default;
};