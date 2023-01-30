#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"

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
  bool has_timer_scheduled;
};