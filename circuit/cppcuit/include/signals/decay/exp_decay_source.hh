#pragma once

#include <cstdint>
#include <nlohmann/json_fwd.hpp>
#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"
#include "timer/timer_queue.hh"

// This generates decay values on a timer for ewmas and exponential decays
// This is done on a timer instead of on each tick
// to limit the amount of compute propagated by any single event that updates
// time, meaning that the major 'whole tree updates' tend to be
// relegated to timer calls maintaining state
class ExpDecaySource {
  // Since this is running on a timer, one could theoretically cache the
  // expected decay? would have to ensure we get exact or close-to-exact timer
  // ticks

  double inv_half_life_ns;
  std::uint64_t last_decay;
  std::uint64_t reschedule_decay_timer;

  double compute_decay(std::uint64_t now, TimerHandle reschedule);
  void do_init(TimerHandle timer, const nlohmann::json &json);

public:
  using Decay = double;

  template <class O, class M>
    requires(HAS_REF_FIELD(O, Decay, decay) &&
             HAS_FIELD(M, TimerHandle, timer) &&
             HAS_FIELD(M, CircuitTime, time)) bool
  decay(O output, M metadata) {
    // TODO make time a metadata
    output.decay = this->compute_decay(metadata.time, metadata.timer);
    return true;
  }
  template <class O, class M>
    requires(HAS_REF_FIELD(O, double, decay) &&
             HAS_FIELD(M, TimerHandle, timer))
  void init(O output, M metadata, const nlohmann::json &json) {
    output.decay = 0;
    do_init(metadata.timer, json);
  }
};