#include "signals/book_pressure/book_impulse_tracker.hh"

double BookImpulseTracker::update_levels(const DepthUpdate *updates) {
  auto updater = [this](Side side, const Level new_level, double &data) {
    this->impulse_tracker.add_impulse(side, new_level.price(),
                                      new_level.size() - data);
    data = new_level.size();
    return new_level.size() == 0 ? LevelDecision::Discard : LevelDecision::Keep;
  };

  auto creator = [this](Side side, Level new_level) {
    this->impulse_tracker.add_impulse(side, new_level.price(),
                                      new_level.size());
    return std::optional<double>(new_level.size());
  };

  book.update_levels(updates, creator, updater);

  return this->impulse_tracker.compute_fair();
}