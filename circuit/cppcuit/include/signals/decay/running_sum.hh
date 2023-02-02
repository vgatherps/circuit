#pragma once

#include <cstdint>
#include <nlohmann/json_fwd.hpp>

#include "cppcuit/runtime_error.hh"

#include "cppcuit/signal_requirements.hh"
#include "timer/timer_queue.hh"

class RunningSum {
public:
  using RunningSumOut = double;

  template <class A, class O>
    requires(HAS_OPT_REF(A, double, tick) &&
             HAS_REF_FIELD(O, double, running_sum))
  static void on_tick(A input, O output) {
    if (!input.tick.valid()) {
      return;
    }
    output.running_sum += *input.tick;
  }

  template <class A, class O>
    requires(HAS_ARR_OPT(A, double, decay) &&
             HAS_REF_FIELD(O, double, running_sum))
  static void decay(A input, O output) {
    if (input.decay.valid()) {
      output.running_sum *= input.decay;
    }
  }

  RunningSum() = default;
};