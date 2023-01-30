#pragma once

#include <cstdint>
#include <type_traits>

#include "fast_exp_64.hh"

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"
#include "timer/timer_queue.hh"

// This generates decay values on a timer for ewmas and exponential decays
// This is done on a timer instead of on each tick
// to limit the amount of compute propagated by any single event that updates
// time, meaning that the major 'whole tree updates' tend to be
// relegated to timer calls maintaining state
class DecaySource {
  // Since this is running on a timer, one could theoretically cache the
  // expected decay? would have to ensure we get exact or close-to-exact timer
  // ticks

  double inv_half_life;
  std::uint64_t last_decay;

public:
  template <class I, class O, class M>
    requires(HAS_OPT_REF(I, std::uint64_t, time) &&
             HAS_FIELD(M, TimerHandle, timer))
  void decay(I input, O output, M metadata) {
    // TODO make time a metadata
    if (input.time.valid()) [[likely]] {
      double decayed_sum =
          this->compute_decay(*input.time, output.running_sum, metadata.timer);

      output.running_sum = decayed_sum;
    } else {
      // this is an outright error, tbh. should either raise exception,
      // assume optimizer removes it? assert? make time sp special that
      // it's literally always valid?
      cold_runtime_error("Time was invalid, impossible");
    }
  }
};