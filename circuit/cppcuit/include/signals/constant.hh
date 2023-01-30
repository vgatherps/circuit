#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

// A constant which is always constructed as part of inline default constructor
template <class T> class CtorConstant {
public:
  using Output = T;
};