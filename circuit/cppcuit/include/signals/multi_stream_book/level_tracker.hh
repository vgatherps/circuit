#pragma once

#include "level_event.hh"

#include <cassert>
#include <cmath>
#include <optional>
#include <ranges>
#include <vector>

// lol doubles for prices and sizes. Will just do epsilon tracking here
// In real world these are fixed point / integer

inline bool is_zero(double d) { return std::abs(d) < 1e-7; }
inline bool is_positive(double d) { return d >= 1e-7; }
inline bool is_nonnegative(double d) { return d >= -1e-7; }

template <class Ts> struct TimestampedOffset {
  Ts time;
  double trade_size;
  double implied_add;
};

template <class Ts> class TsLevelTracker {
  std::vector<TimestampedOffset<Ts>> expected_trades;
  double diff_size = 0;
  Ts last_ts;
  std::optional<Ts> marked_for_deletion_at;

  void validate() const {
    for (const auto &trade : expected_trades) {
      assert(trade.trade_sz >= trade.implied_add);
      assert(is_positive(trade.trade_sz));
      assert(is_positive(trade.implied_add));
    }

    // assert(total_size_removal() >= Fixed128::zero());
    // assert(total_size_removal() <= self.diff_size);
    // assert(inferred_size() >= Fixed128::zero());
    // assert(inferred_size() <= self.diff_size);

    // If we are marked for deletion, this only includes trades that come
    // after the deletion event. This should hence be net neutral
    /*
    if self
      .marked_for_deletion_at.is_some() {
        debug_assert_eq !(self.total_size_removal(), Fixed128::zero())
      }
      */
  }

public:
  TsLevelTracker(Ts t) : last_ts(std::move(t)) {}

  TsLevelTracker() = default;
  TsLevelTracker(const TsLevelTracker &) = default;
  TsLevelTracker(TsLevelTracker &&) = default;
  TsLevelTracker &operator=(const TsLevelTracker &) = default;
  TsLevelTracker &operator=(TsLevelTracker &&) = default;

  Ts last_size_time() const {
    // We write this to None if it's stale, so it only
    // exists conditional on being newer
    return marked_for_deletion_at.value_or(last_ts);
  }

  double total_size_removal() const {

    double to_remove = 0.;
    for (const auto &trade : expected_trades) {
      if (marked_for_deletion_at.has_value() &&
          *marked_for_deletion_at < trade.time) {
        to_remove += trade.trade_sz - trade.implied_add;
      }
    }

    return to_remove;
  }

  double inferred_size() const {
    if (marked_for_deletion_at.has_value()) {
      return 0.;
    }
    double rval = diff_size - total_size_removal();
    assert(is_nonnegative(rval));
    return rval;
  }

  void mark_for_deletion(Ts delete_time, std::vector<LevelEvent> &events) {
    validate();

    if (delete_time <= last_size_time()) {
      return;
    }

    validate();
  }
};

using LevelTracker = TsLevelTracker<std::uint64_t>;