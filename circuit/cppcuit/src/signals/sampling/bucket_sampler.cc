#include "signals/sampling/bucket_sampler.hh"

#include <nlohmann/json.hpp>

void TradeBucketSampler::do_init(const nlohmann::json &params) {
  // another huge hack until parameters
  try {
    minimum_weight = params["minimum_weight"].get<double>();
    initial_weight = params["initial_weight"].get<double>();
    trade_weight = params["trade_weight"].get<double>();
  } catch (...) {
    initial_weight = 10;
    minimum_weight = -10;
    trade_weight = 0.1;
  }
  current_weight = initial_weight;
}