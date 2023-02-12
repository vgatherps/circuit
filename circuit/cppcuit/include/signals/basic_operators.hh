#pragma once

#include <tuple>
#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

template <class A, class B>
  requires(std::is_copy_constructible_v<A> && std::is_copy_constructible_v<B>)
class Join2 {
public:
  // Probably want to do this by taking advantage of the call itself?
  struct Input {
    optional_reference<const A> a;
    optional_reference<const B> b;
  };

  using Output = std::tuple<A, B>;

  template <class O>
    requires HAS_REF_FIELD(O, Output, out)
  static bool call(Input inputs, O o) {
    if (inputs.a.valid() && inputs.b.valid()) {
      out.out = {*inputs.a, *inputs.b};
      return true;
    } else {
      return false;
    }
  }
};

template <class A, std::size_t Idx>
  requires(std::is_copy_assignable_v<A>)
class StaticIndex {

public:
  using Output = A;

  template <class I, class O, std::size_t N>
    requires(
        requires(I in) {
          { in.a.valid() } -> std::is_same_v<bool>
        } && requires(I in, A &a) { a = std::tuple_element<Idx>(*in.a) } &&
        HAS_REF_FIELD(O, Output, out))
  static bool call(I inputs, O o) {
    if (inputs.a.valid()) {
      out.out = std::tuple_element<Idx>(*inputs.a);
      return true;
    } else {
      return false;
    }
  }
};