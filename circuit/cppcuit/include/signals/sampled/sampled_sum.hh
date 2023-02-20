#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"

template <class A>
requires(std::is_default_constructible_v<A> &&requires(A a, A b) {
  a += b;
}) class SampledSum {

  bool period_valid = true;

public:
  struct Input {
    optional_reference<const A> a;
  };

  template <class O>
  requires HAS_REF_FIELD(O, Output, out)
  bool call(Input inputs, O &o) {
    if (inputs.a.valid() && period_valid) {
      o.out += *inputs.a;
    } else {
      period_valid = false
    }
    return period_valid;
  }

  bool reset(auto, auto) { return period_valid; }

  template <class I, class O>
  requires HAS_OPT_REF(I, A, a) && HAS_REF_FIELD(O, Output, out)
  bool reset_cleanup(I inputs, O &o) {
    period_valid = true;
    o.out = A();
    return true;
  }
};