#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"

template <class A, bool IsMin>
requires(std::is_copy_constructible_v<A> &&requires(A a, A b) {
  a > b || a < b;
}) class SampledMinMax {

  bool has_value = false;

public:
  struct Input {
    optional_reference<const A> a;
  };

  template <class O>
  requires HAS_REF_FIELD(O, Output, out)
  bool call(Input inputs, O &o) {
    if (inputs.a.valid()) {
      if (has_value) {
        if constexpr (IsMin) {
          if (*inputs.a < out.out) {
            out.out = *inputs.a;
          }
        } else if (*inputs.a > out.out) {
          out.out = *inputs.a;
        }
      } else {
        has_value = true;
        out.out = *inputs.a;
      }
    }
    return has_value;
  }

  bool reset(auto, auto) { return has_value; }

  template <class I, class O>
  requires HAS_OPT_REF(I, A, a) && HAS_REF_FIELD(O, Output, out)
  bool reset_cleanup(I inputs, O &o) {
    has_value = inputs.a.valid();
    return has_value;
  }
};

template <class A> using SampledMin = SampledMinMax<A, true>;
template <class A> using SampledMax = SampledMinMax<A, false>;