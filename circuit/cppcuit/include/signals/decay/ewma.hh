#pragma once

#include <cstdint>
#include <nlohmann/json_fwd.hpp>

#include "cppcuit/runtime_error.hh"

#include "cppcuit/signal_requirements.hh"
#include "timer/timer_queue.hh"

class Ewma {
  bool has_value = false;

public:
  using EwmaOut = double;

  template <class I, class A, class O>
    requires(HAS_OPT_REF(I, double, signal) && HAS_ARR_OPT(A, double, decay) &&
             HAS_REF_FIELD(O, double, ewma)) bool
  decay(I input, A arr_input, O output) {

    if (!input.signal.valid()) [[unlikely]] {
      has_value = false;
      return false;
    }

    double new_value = *input.signal;

    if (has_value) [[likely]] {
      if (arr_input.decay.valid()) [[likely]] {
        double decay_by = *arr_input.decay;
        assert(decay_by <= 1.0);
        assert(decay_by >= 0.0);

        // (1.0 - decay) * new_value
        // equal to new_value - decay_by * new_value
        // which directly translates to fnmadd
        double update_with = new_value - decay_by * new_value;
        output.ewma *= (decay_by + update_with);
      }
    } else {
      output.ewma = new_value;
    }
    return true;
  }

  Ewma() = default;
};