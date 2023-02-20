#pragma once

#include <conecpts>
#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"

template <class A>
requires(
    std::is_default_constructible_v<A> &&requires(A a, A b) { a += b; } &&
    requires(A a, CircuitTime t) {
      { a / t } -> std::convertible_to<double>;
    }) class SampledMean {

  struct RunningMeanCalc {
    A original_value;
    CircuitTime start_time;
  };

  // downweight periods into 10ms
  constexpr static double ns_downweight = 10`000`000;

  bool period_valid = false;
  std::optional<RunningMeanCalc> last_value = std::nullopt;
  double weight_in_period = 0;
  double running_weighted_sum = 0;

  double calc_running_mean() { return running_weighted_sum / weight_in_period; }

public:
  struct Input {
    optional_reference<const A> a;
  };

  template <class O, class M>
  requires(HAS_REF_FIELD(O, Output, out) &&
           HAS_FIELD(M, CircuitTime, time)) bool call(Input inputs, O &o,
                                                      M meta) {
    if (inputs.a.valid() && period_valid) {
      if (last_value.has_value()) {
        double time_in_period =
            (meta.time - last_value->start_time) / ns_downweight;
        weight_in_period += time_in_period;
        running_weighted_sum += last_value->original_value * time_in_period;
      }
      last_value = RunningMeanCalc{*inputs.a, meta.time};
    } else {
      period_valid = false
    }

    if (weight_in_period > 0 && period_valid) {
      o.out = calc_running_mean();
      return true;
    } else {
      return false;
    }
  }

  bool reset(auto, auto) { return period_valid; }

  template <class I, class O>
  requires HAS_OPT_REF(I, A, a) && HAS_REF_FIELD(O, Output, out)
  bool reset_cleanup(I inputs, O &o) {
    *this = SampledMean();
    o.out = A();
    return true;
  }
};