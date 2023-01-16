#include "signals/book_pressure/book_impulse_tracker.hh"

std::optional<double> BookImpulseTracker::update_levels(UpdatedLevels updates) {
  auto compute_for_side = [this](Side s, std::span<AnnotatedLevel> levels) {
    for (const AnnotatedLevel &level : levels) {
      double impulse = level.current_size - level.previous_size;
      this->impulse_tracker.add_impulse(s, level.price, impulse);
    }
  };

  compute_for_side(Side::Buy, updates.bids);
  compute_for_side(Side::Sell, updates.asks);
  return this->impulse_tracker.compute_fair();
}

std::optional<double>
BookImpulseTracker::update_reference(std::optional<double> new_ref,
                                     const BookBuilder<double, double> &book) {
  if (new_ref.has_value()) [[likely]] {
    bool was_invalid = !impulse_tracker.is_valid();
    impulse_tracker.set_reference(*new_ref);
    if (was_invalid) [[unlikely]] {
      recompute_from_book(book);
    }
  } else {
    impulse_tracker = LinearBookImpulse(impulse_tracker.get_scale());
  }

  return impulse_tracker.compute_fair();
}

void BookImpulseTracker::recompute_from_book(
    const BookBuilder<double, double> &book) {
  auto add_for_side = [this](Side s, double price, double size) {
    this->impulse_tracker.add_impulse(s, price, size);
  };

  for (auto bids = book.bids_begin(); bids != book.bids_end(); ++bids) {
    add_for_side(Side::Buy, bids->first, bids->second);
  }
  for (auto asks = book.asks_begin(); asks != book.asks_end(); ++asks) {
    add_for_side(Side::Sell, asks->first, asks->second);
  }
}