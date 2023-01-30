#include "signals/book_pressure/book_updater.hh"

std::optional<BBO> BookUpdater::update_levels(const DepthUpdate *updates,
                                              PlainBook &book,
                                              UpdatedLevels &levels) {
  levels.bids.clear();
  levels.asks.clear();

  auto vec_for_side = [&levels](Side s) -> std::vector<AnnotatedLevel> & {
    if (s == Side::Buy) {
      return levels.bids;
    } else {
      return levels.asks;
    }
  };
  auto updater = [&vec_for_side](Side side, const BookLevel new_level,
                                 double &data) {
    AnnotatedLevel annotated{.price = new_level.price,
                             .previous_size = data,
                             .current_size = new_level.size};
    vec_for_side(side).push_back(annotated);
    data = new_level.size;
    return new_level.size == 0.0 ? LevelDecision::Discard : LevelDecision::Keep;
  };

  auto creator = [&vec_for_side](Side side, BookLevel new_level) {
    if (new_level.size > 0.0) {

      AnnotatedLevel annotated{.price = new_level.price,
                               .previous_size = 0,
                               .current_size = new_level.size};
      vec_for_side(side).push_back(annotated);
      return std::optional<double>(new_level.size);
    } else {
      return std::optional<double>{};
    }
  };

  book.update_levels(updates, creator, updater);

  return book.bbo();
}