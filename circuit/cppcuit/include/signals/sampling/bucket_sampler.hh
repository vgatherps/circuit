#pragma once

#include <nlohmann/json_fwd.hpp>

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"

#include <iostream>

// very rudimentary bucket based sampler
// Not one I would advertise for production
// For one want the pseudo-L3 book I haven't implemented yet
// (infer true set of trades / adds / cancels)
// to get better sample on trade vs add vs cancel
// and also want to normalize by volume -
// would have a target of N samples per day and
// can run a fitting process to get there
// by counting samples.
//
// More spohisticated sampling research would entail
// Rerunning training processes and optimizing for PnL

class TradeBucketSampler {

  double minimum_weight;
  double initial_weight;
  double trade_weight;

  double current_weight;

  void do_init(const nlohmann::json &params);

public:
  using Sample = bool;
  using ConstTradeUpdate = const Trade *;

  template <class I, class O>
  bool on_trade(I inputs, O outputs)
    requires(HAS_OPT_REF(I, ConstTradeUpdate, trade) &&
             HAS_REF_FIELD(O, bool, should_sample))
  {
    if (inputs.trade.valid()) {
      current_weight -= trade_weight;
    }

    if (current_weight <= 0.0) {
      current_weight += initial_weight;
      outputs.should_sample = true;
    } else {
      outputs.should_sample = false;
    }

    current_weight = std::max(minimum_weight, current_weight);
    return true;
  }

  template <class I, class O>
  bool cleanup(I, O outputs)
    requires HAS_REF_FIELD(O, bool, should_sample)
  {
    outputs.should_sample = false;
    return true;
  }

  template <class O>
    requires(HAS_REF_FIELD(O, bool, should_sample)) bool
  init(O output, const nlohmann::json &params) {
    output.should_sample = false;
    this->do_init(params);
    return true;
  }
};