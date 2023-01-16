#pragma once

#include "linear_impulse.hh"
#include "signals/bookbuilder.hh"

class BookImpulseTracker {
  LinearBookImpulse impulse_tracker;

  void recompute_from_book(const BookBuilder<double, double> &book);

public:
  std::optional<double> update_levels(UpdatedLevels updates);

  std::optional<double>
  update_reference(std::optional<double> new_ref,
                   const BookBuilder<double, double> &book);
};