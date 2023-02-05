#pragma once

#include <nlohmann/json_fwd.hpp>
#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

// A constant which is always constructed as part of inline default constructor

// TODO make generic version

class DoubleParameter {

  static void do_init(double &, const nlohmann::json &);

public:
  using Output = double;

  template <class O>
    requires(HAS_REF_FIELD(O, Output, out))
  static void init(O output, const nlohmann::json &params) {
    do_init(output.out, params);
  }
};