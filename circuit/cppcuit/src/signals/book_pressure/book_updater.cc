#include "signals/book_pressure/book_updater.hh"

std::optional<BBO> BookUpdater::update_levels(const DepthUpdate *updates,
                                              PlainBook &book) {
  this->bid_changes.clear();
  this->ask_changes.clear();

  auto vec_for_side = [this](Side s) -> std::vector<AnnotatedLevel> & {
    if (s == Side::Buy) {
      return bid_changes;
    } else {
      return ask_changes;
    }
  };
  auto updater = [this, &vec_for_side](Side side, const BookLevel new_level,
                                       double &data) {
    AnnotatedLevel annotated{.current_size = new_level.size,
                             .previous_size = data,
                             .price = new_level.price};
    vec_for_side(side).push_back(annotated);
    data = new_level.size;
    return new_level.size == 0.0 ? LevelDecision::Discard : LevelDecision::Keep;
  };

  auto creator = [this, &vec_for_side](Side side, BookLevel new_level) {
    if (new_level.size > 0.0) {

      AnnotatedLevel annotated{.current_size = new_level.size,
                               .previous_size = 0,
                               .price = new_level.price};
      vec_for_side(side).push_back(annotated);
      return std::optional<double>(new_level.size);
    } else {
      return std::optional<double>{};
    }
  };

  book.update_levels(updates, creator, updater);

  auto bids_iter = book.bids_begin();
  auto asks_iter = book.asks_begin();

  if (bids_iter != book.bids_end() && asks_iter != book.asks_end()) {
    return BBO{
        .bid = {.price = bids_iter->first, .size = bids_iter->second},
        .ask = {.price = asks_iter->first, .size = asks_iter->second},
    };
  } else {
    return std::nullopt;
  }
}