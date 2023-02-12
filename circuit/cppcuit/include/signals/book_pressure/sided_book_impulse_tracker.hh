#pragma once

#include "linear_impulse.hh"

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"
#include "timer/timer_queue.hh"

#include <nlohmann/json_fwd.hpp>

class SidedBookImpulseTracker {

  double scale;

  void handle_updates(const UpdatedLevels &updates, double fair,
                      double &bid_impulse, double &ask_impulse);

  void do_init(const nlohmann::json &json);

public:
  using FairPrice = double;

  template <class I, class O>
    requires HAS_OPT_REF(I, UpdatedLevels, updates) &&
             HAS_REF_FIELD(O, double, bid_impulse) &&
             HAS_REF_FIELD(O, double, ask_impulse)
  void on_book_updates(I inputs, O outputs) {
    outputs.bid_impulse = 0.0;
    outputs.ask_impulse = 0.0;
    if (inputs.updates.valid() && inputs.fair.valid()) [[likely]] {
      handle_updates(*inputs.updates, *inputs.book, outputs.bid_impulse,
                     outputs.ask_impulse);
    }
  }

  template <class O, class M>
    requires(HAS_REF_FIELD(O, double, fair)) bool
  init(O output, M metadata, const nlohmann::json &params) {
    this->do_init(params);
    return false;
  }
};