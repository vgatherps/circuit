#pragma once

#include <cassert>
#include <cstdint>
#include <optional>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"
#include "md_types/trade_message_generated.h"
#include "signals/trade_pressure/tick_detector.hh"
#include "timer/timer_queue.hh"

#include <nlohmann/json_fwd.hpp>

// This part of the trade pressure signal aggregates the ticks per-market
// broadcasts an event whenever a 'tick' occurs
// and maintains a running sum of trades believed to be part of the current tick

// TODO can we decompose this further into a pipeline
// where no single object holds more than one parameter?
// that makes it trivial to spray-and-pray parameters
// while deduplicating computations done
// on the same parameter set!

struct PerMarketParams {
  double book_weight;
  double pricesize_weight;
  double distance_weight;
};

struct RunningImpulseManager {
  double current_pricesize;
  double current_impulse;
  double deepest_price;
  double distance_score;

  // TODO should store side here for validation?

  inline double impulse() const {
    return this->distance_score * this->current_impulse;
  }
  bool is_empty() const { return this->current_pricesize == 0.0; }
};

class SingleTickAggregator {
  PerMarketParams params;

  RunningImpulseManager running;

  void mark_tick_finished(double impulse, double &tick, double &running,
                          bool &tick_valid) {
    tick = impulse;
    running = 0.0;
    tick_valid = true;
    this->running = RunningImpulseManager{};
  }
  double handle_trade(const Trade *trades, double fair);

public:
  using RunningTickScore = double;
  using NewTickScore = double;

  template <class O>
  constexpr static bool HasTickRunning =
      HAS_REF_FIELD(O, NewTickScore, tick) &&
      HAS_REF_FIELD(O, RunningTickScore, running);

  struct OnTradeOutput {
    bool tick;
  };

  // Takes trade struct, current fair
  // Outputs the running score and potentially a tick

  template <class I, class O>
    requires(HAS_OPT_REF(I, ConstTradeUpdate, trade) &&
             HAS_OPT_REF(I, double, fair) &&
             HAS_REF_FIELD(O, RunningTickScore, running))
  void on_trade(I inputs, O outputs) {
    // if the trade is invalid, don't waste time reasoning about ticks...
    // could be complex with the whole 'end-of-tick', but tbh assume
    // we're not getting a whole lot of secretly invalid end-of-ticks
    // and also the end-of-tick watchdog will save us anyways

    if (inputs.trade.valid()) [[likely]] {

      // we only do the real computation if the fair is valid, but as a safety
      // check, forward ticks regardless
      double current_impulse;
      if (inputs.fair.valid()) [[likely]] {
        current_impulse =
            this->handle_trade(*inputs.trade, (*inputs.trade)->price());
      } else {
        current_impulse = this->running.impulse();
      }

      outputs.running = current_impulse;
    }
  }

  // Takes a dummy tick input
  // Sets running score to zero and potentially outputs a current tick
  template <class I, class O>
    requires(HAS_OPT_REF(I, Tick, tick) && HasTickRunning<O>)
  OnTradeOutput on_tick(I inputs, O outputs) {

    OnTradeOutput outputs_valid;

    if (this->running.is_empty() || !inputs.tick.valid()) {
      outputs_valid.tick = false;
    } else {
      mark_tick_finished(this->running.impulse(), outputs.tick, outputs.running,
                         outputs_valid.tick);
    }

    outputs.running = 0;

    return outputs_valid;
  }

  template <class I, class O>
    requires(HAS_OPT_REF(I, ConstTradeUpdate, trade) &&
             HAS_OPT_REF(I, double, fair) && HAS_OPT_REF(I, Tick, tick) &&
             HasTickRunning<O>)
  OnTradeOutput on_ticked_trade(I inputs, O outputs) {
    OnTradeOutput tick_validity = on_tick(inputs, outputs);
    on_trade(inputs, outputs);
    return tick_validity;
  }

  template <class O>
    requires(HasTickRunning<O>)
  OnTradeOutput init(O outputs, const nlohmann::json &) {
    outputs.running = 0.0;
    outputs.tick = 0.0;
    this->params.pricesize_weight = 0.0001;

    return {.tick = false};
  }
};