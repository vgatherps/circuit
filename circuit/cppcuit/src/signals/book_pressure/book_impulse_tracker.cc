#include "signals/book_pressure/book_impulse_tracker.hh"

#include "cppcuit/runtime_error.hh"

#include <nlohmann/json.hpp>

#include <iostream>

std::optional<double>
BookImpulseTracker::handle_updates(const UpdatedLevels &updates,
                                   const PlainBook &book) {

  if (impulse_tracker.is_valid()) [[likely]] {

    auto compute_for_side = [this](Side s,
                                   const std::vector<AnnotatedLevel> &levels) {
      for (const AnnotatedLevel &level : levels) {
        double impulse = level.current_size - level.previous_size;
        this->impulse_tracker.add_impulse(s, level.price, impulse);
      }
    };

    compute_for_side(Side::Buy, updates.bids);
    compute_for_side(Side::Sell, updates.asks);
  } else {
    impulse_tracker = LinearBookImpulse(impulse_tracker.get_scale(), book);
  }
  std::optional<double> maybe_fair = this->impulse_tracker.compute_fair();

  std::optional<double> old_reference = impulse_tracker.reference_price();

  if (impulse_tracker.out_of_range(1e7)) [[unlikely]] {
    impulse_tracker = LinearBookImpulse(impulse_tracker.get_scale(), book);
    maybe_fair = impulse_tracker.compute_fair();
  }

  if (maybe_fair.has_value() && !std::isfinite(*maybe_fair)) {
    maybe_fair = std::nullopt;
  }

  return maybe_fair;
}

void BookImpulseTracker::recompute_from_book(
    std::uint64_t now, optional_reference<const PlainBook> book,
    TimerHandle reschedule) {

  if (book.valid()) [[likely]] {

    std::optional<double> last_fair = impulse_tracker.compute_fair();
    auto old_impulse = impulse_tracker;

    impulse_tracker = LinearBookImpulse(impulse_tracker.get_scale(), *book);

    if (last_fair.has_value()) {
      std::optional<double> new_fair = impulse_tracker.compute_fair();

      double old_ref = *(impulse_tracker.reference_price());

      if (!new_fair.has_value()) {
        cold_runtime_error(
            "Book fair become invalid after getting a book recompute");
      }

      double rel_diff = (*last_fair - *new_fair) / *last_fair;

      if (std::abs(rel_diff) > 0.0000) {
        if (std::abs(rel_diff) > 0.0001) {
          cold_runtime_error("Book fair changed significantly on recompute");
        }
      }
    }
  }

  // Force recompute once every 30 seconds
  std::uint64_t next_recompute = 1'000'000'000ULL * 30;

  reschedule.schedule_call_at(next_recompute + now);
}

void BookImpulseTracker::do_init(const nlohmann::json &json) {
  double scale = json["scale"].get<double>();
  impulse_tracker = LinearBookImpulse(scale);
}