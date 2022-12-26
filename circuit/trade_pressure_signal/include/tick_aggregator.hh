#pragma once

#include <cassert>
#include <cstdint>
#include <optional>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

#include "timer/timer_queue.hh"

#include <nlohmann/json_fwd.hpp>

#include <md_types/trade_message_generated.h>

struct Tick {};

// This part of the trade pressure signal aggregates the ticks per-market
// and broadcasts an event whenever a 'tick' occurs
//
// This, like everything in trade pressure, will require a respectable timer
// interface...
//
// Will just have to assume that away for now
// will be a good next-week project! get a real
// version of trade pressure working!

inline double weight_distance_for(double price, double fair, double weight,
                                  Side side) {
  constexpr double SideAdjustments[] = {0.0, 2.0};
  double ratio = price / fair;
  ratio -= SideAdjustments[(int)side];

  return ratio;
}

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

using ConstTradeUpdate = const TradeUpdate *; 

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
  double handle_trades(const TradeUpdate *trades, double fair);

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

  // REQUIRED TODOS FOR THIS ONE:
  // 1. always-valid. In this case running is just outright ALWAYS valid
  template <class I, class O>
    requires(HAS_OPT_REF(I, ConstTradeUpdate, trades) &&
             HAS_OPT_REF(I, double, fair) &&
             HAS_OPT_REF(I, bool, end_of_tick) && HasTickRunning<O>)
  OnTradeOutput on_trade(I inputs, O outputs) {

    OnTradeOutput outputs_valid = {.tick = false};

    // if the trade is invalid, don't waste time reasoning about ticks...
    // could be complex with the whole 'end-of-tick', but tbh assume
    // we're not getting a whole lot of secretly invalid end-of-ticks
    // and also the end-of-tick watchdog will save us anyways

    if (inputs.trades.valid()) [[likely]] {

      // we only do the real computation if the fair is valid, but as a safety
      // check, forward ticks regardless
      double current_impulse;
      if (inputs.fair.valid()) [[likely]] {
        current_impulse =
            this->handle_trades(*inputs.trades, *inputs.fair);
      } else {
        current_impulse = this->running.impulse();
      }

      if (inputs.end_of_tick.valid() && *inputs.end_of_tick) {
        mark_tick_finished(current_impulse, outputs.tick, outputs.running,
                           outputs_valid.tick);
      } else {
        outputs.running = current_impulse;
      }
    }

    return outputs_valid;
  }

  // Takes a dummy tick input
  // Sets running score to zero and potentially outputs a current tick
  template <class I, class O>
    requires(HAS_OPT_REF(I, double, tick) && HasTickRunning<O>)
  OnTradeOutput on_end_tick(I inputs, O outputs) {

    OnTradeOutput outputs_valid;

    if (this->running.is_empty()) {
      outputs_valid.tick = false;
    } else {
      mark_tick_finished(this->running.impulse(), outputs.tick, outputs.running,
                         outputs_valid.tick);
    }

    outputs.running = 0;

    return outputs_valid;
  }

  template <class O>
    requires(HasTickRunning<O>)
  OnTradeOutput init(O outputs, const nlohmann::json &) {
    outputs.running = 0.0;
    outputs.tick = 0.0;

    return {.tick = false};
  }
};