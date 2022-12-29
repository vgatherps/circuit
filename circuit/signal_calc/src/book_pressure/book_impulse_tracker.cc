#include "book_pressure/book_impulse_tracker.hh"

  void BookImpulseTracker::update_levels(const DepthUpdate *updates) {
    float impulses[2] = {0.0};
    auto updater = [&](Side side, const Level new_level, double &data) {
        impulses[(std::size_t)side] += new_level.size() - data;
        data = new_level.size();
        return new_level.size() == 0 ? LevelDecision::Discard : LevelDecision::Keep;
    };
  
    auto creator = [&](Side side, Level new_level) {
        impulses[(std::size_t)side] += new_level.size();
        return std::optional<double>(new_level.size());
    };

    book.update_levels(updates, creator, updater);
  }