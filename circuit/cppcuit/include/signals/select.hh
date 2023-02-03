#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

template <class A> class Selector {
public:
  // Probably want to do this by taking advantage of the call itself?
  struct Input {
    optional_reference<const A> a;
    optional_reference<const A> b;
    optional_reference<const bool> select_a;
  };

  using Output = A;

  template <class O>
    requires HAS_REF_FIELD(O, Output, out)
  static bool call(Input inputs, O &out) {
    if (inputs.select_a.valid()) [[likely]] {
      if (*inputs.select_a) {
        if (inputs.a.valid()) [[likely]] {
          out.out = *inputs.a;
          return true;
        }
      } else {
        if (inputs.b.valid()) [[likely]] {
          out.out = *inputs.b;
          return true;
        }
      }
    }
    return false;
  }
};
