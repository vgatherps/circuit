#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

// A constant which is always constructed as part of inline default constructor
// TODO this can get merged with the triggerable constant
// now that we have optional inputs
template <class T> class CtorConstant {
public:
  using Output = T;
};

// A constant where validity can be updated
template <class T> class TriggerableConstant {
public:
  using Output = T;

  template <class I, class O>
    requires requires(I input, bool b) { b = input.tick.valid(); }
  static bool tick(I input, O) {
    return input.tick.valid();
  }
};