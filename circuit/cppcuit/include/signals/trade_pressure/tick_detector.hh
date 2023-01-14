#pragma once

#include <cassert>
#include <cstdint>
#include <optional>

#include <nlohmann/json_fwd.hpp>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"
#include "md_types/trade_message_generated.h"
#include "timer/timer_queue.hh"

struct Tick {};
using ConstTradeUpdate = const Trade *;

// This generates an event when it's detected that the current batch of trades
// has likely ended - crypto exchanges send out many individual trade events
// corresponding to a single take, but don't mark the end.

// Ostensibly this could be part of the tick aggregator, but the timer
// is too rudimentary for that. This ability is required to correctly
// handle ftx-style heavily aggregated batches

class TickCompletionDetector {

  std::uint64_t us_till_batch_ends;
  std::uint64_t ns_till_batch_invalidation;
  std::uint64_t last_received_timestamp;
  std::optional<Trade> last_trade_in_batch;

  bool is_invalidation_scheduled;

  void schedule_invalidation_at(std::uint64_t invalidate_at,
                                TimerHandle handle);

  bool handle_trade(const Trade *trade, std::uint64_t local_timestamp,
                    TimerHandle reschedule) {
    bool new_tick = false;
    if (last_trade_in_batch.has_value()) {
      new_tick |= trade->buy() != last_trade_in_batch->buy();
      new_tick |=
          (trade->exchange_time_us() -
           last_trade_in_batch->exchange_time_us()) > us_till_batch_ends;
    }

    // I think we could hoist this check inside the last_trade_has_value check,
    // since if we have a valid trade, I think that implies we have a scheduled
    // timer
    if (!is_invalidation_scheduled) {
      schedule_invalidation_at(local_timestamp + ns_till_batch_invalidation,
                               reschedule);
    }

    last_received_timestamp = local_timestamp;
    last_trade_in_batch = *trade;
    return new_tick;
  }

void do_init(const nlohmann::json &params);

public:
  using TickOutput = Tick;

  // will need a timer callback here
  // todo - don't schedule on every trade,
  // only schedule if:
  // 1. a callback is not scheduled
  // 2. we're inside the callback, and have a new expiry time
  template <class I, class O, class M>
    requires(HAS_OPT_REF(I, ConstTradeUpdate, trade) &&
             HAS_OPT_REF(I, std::uint64_t, time) &&
             HAS_REF_FIELD(O, TickOutput, tick) &&
             HAS_FIELD(M, TimerHandle, timer)) bool
  on_trade(I inputs, O outputs, M metadata) {
    if (inputs.trade.valid()) [[likely]] {
      return this->handle_trade(*inputs.trade, *inputs.time, metadata.timer);
    } else {
      return false;
    }
  }

  template <class I, class O, class M>
    requires(HAS_OPT_REF(I, std::uint64_t, time) &&
             HAS_REF_FIELD(O, Tick, tick) &&
             HAS_FIELD(M, TimerHandle, timer)) bool
  invalidate(I input, O output, M metadata) {

    if (last_trade_in_batch.has_value()) {
      std::uint64_t invalidate_at =
          last_received_timestamp + ns_till_batch_invalidation;
      if (*input.time >= invalidate_at) {
        return true;
      } else {
        schedule_invalidation_at(invalidate_at, metadata.timer);
      }
    }

    // otherwise, no running trade to invalidate
    return false;
  }

  template <class O>
    requires(HAS_REF_FIELD(O, Tick, tick))
  bool init(O output, const nlohmann::json &params) {
    this->do_init(params);
    return false;
  }
};