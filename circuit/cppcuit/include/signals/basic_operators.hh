#pragma once

#include <concepts>
#include <tuple>
#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

template <std::size_t Idx, class A>
  requires(std::is_copy_assignable_v<A>)
class StaticIndex;

template <std::size_t Idx, class A, std::size_t N>
  requires(std::is_copy_assignable_v<A>)
class StaticIndex<Idx, std::array<A, N>> {

public:
  using Output = A;
  using Arr = std::array<A, N>;

  template <class I, class O>
    requires(HAS_OPT_REF(I, Arr, a) && (Idx < N) &&
             HAS_REF_FIELD(O, Output, out))
  static bool call(I inputs, O out) {
    if (inputs.a.valid()) {
      out.out = std::get<Idx>(*inputs.a);
      return true;
    } else {
      return false;
    }
  }
};