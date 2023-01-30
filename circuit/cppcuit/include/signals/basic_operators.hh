#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

template <class A, class B>
requires(std::is_copy_constructible_v<A>
             &&std::is_copy_constructible_v<B>) class Join2 {
public:
  // Probably want to do this by taking advantage of the call itself?
  struct Input {
    optional_reference<const A> a;
    optional_reference<const B> b;
  };

  using Output = std::tuple<A, B>;

  template <class O>
  requires HAS_REF_FIELD(O, Output, out)
  static bool call(Input inputs, O &o) {
    if (inputs.a.valid() && inputs.b.valid()) {
      out.out = {*inputs.a, *inputs.b};
      return true;
    } else {
      return false;
    }
  }
};