#include "signals/parameter.hh"

#include <nlohmann/json.hpp>

void DoubleParameter::do_init(double &d, const nlohmann::json &j) {
  // HUGE hack to get around me not really having any paramterisation layer
  try {
    j.get_to(d);
  } catch (...) {
    d = 0.0;
  }
}