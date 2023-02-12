#include "signals/book_pressure/sided_book_impulse_tracker.hh"

#include "cppcuit/runtime_error.hh"

#include <nlohmann/json.hpp>

#include <iostream>

void SidedBookImpulseTracker::handle_updates(const UpdatedLevels &updates,
                                             double fair, double &bid_impulse,
                                             double &ask_impulse) {

  LinearBookImpulse tracker(scale);
  tracker.set_reference(fair);

  auto compute_for_side =
      [&tracker](Side s, const std::vector<AnnotatedLevel> &levels) {
        for (const AnnotatedLevel &level : levels) {
          double impulse = level.current_size - level.previous_size;
          tracker.add_impulse(s, level.price, impulse);
        }
      };

  compute_for_side(Side::Buy, updates.bids);
  compute_for_side(Side::Sell, updates.asks);

  bid_impulse = tracker.maybe_impulse->bid_ask_impulses[(int)Side::Buy];
  ask_impulse = tracker.maybe_impulse->bid_ask_impulses[(int)Side::Sell];
}

void SidedBookImpulseTracker::do_init(const nlohmann::json &json) {
  json["scale"].get_to(scale);
}