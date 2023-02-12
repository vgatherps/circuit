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

    auto current_inferred_size = inferred_size();
    marked_for_deletion_at = delete_time;

    auto size_to_cancel_first = current_inferred_size;

    auto total_size_to_remove = total_size_removal();

    // If we have a level that is now too small for the trades that we have
    // buffered, we have to regenerate synthetic adds and cancels again
    auto surplus_traded = total_size_to_remove - diff_size;
    assert(total_size_remove >= surplus_traded);

    auto new_inferred_size = inferred_size();
    validate();
  }

  void account_for_surplus_trades_at(double surplus_traded,
                                     double size_to_cancel_first,
                                     std::vector<LevelEvent> &events) {
    if (surplus_traded > 0.0) {
      // First, cancel off the volume BEFORE the add, since we know it's early
      // and part of the diff
      auto should_cancel_later = surplus_traded;
      if (size_to_cancel_first > 0.0) {
        auto remains = std::max(surplus_traded - size_to_cancel_first, 0.0);
        auto can_cancel = std::min(surplus_traded, size_to_cancel_first);

        assert(can_cancel > 0.0);

        events.push_back(Cancel{.size = can_cancel});

        should_cancel_later = remains;
      };
      events.push_back(Add{.size = surplus_traded});

      // We then re-cancel volume that we've seen afterwards since it has to
      // come after the adds
      if (should_cancel_later > 0.0) {
        events.push_back(Cancel{
            .size = should_cancel_later,
        });
      }

      for (auto &trade : expected_trades) {

        if (surplus_traded <= 0.0) {
          break;
        }
        auto possible_add = trade.trade_sz - trade.implied_add;
        assert(possible_add >= 0.0);
        auto new_surplus = surplus_traded - possible_add;
        trade.implied_add += std::min(possible_add, surplus_traded);
        surplus_traded = new_surplus;
      }

      // PROVE we can never have a surplus in excess of traded volume
      // This is because the surplus is bounded from above by the total size
      // to remove and the total size to remove is equal to the total take
      // volume on the books
      assert(surplus_traded <= 0.0);
    }
  }
};

using LevelTracker = TsLevelTracker<std::uint64_t>;