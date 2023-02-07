#include "signals/parameter.hh"

#include <nlohmann/json.hpp>

void RootDoubleParameter::do_init(double &d, const nlohmann::json &j,
                                  bool required) {
  // HUGE hack to get around me not really having any paramterisation layer
  try {
    j.get_to(d);
  } catch (...) {
    if (required) {
      throw;
    }
    d = 0.0;
  }
}