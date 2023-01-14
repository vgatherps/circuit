#pragma once

#include "linear_impulse.hh"
#include "signals/bookbuilder.hh"

class BookImpulseTracker {
  BookBuilder<double, double> book;
  LinearBookImpulse impulse_tracker;

public:
  std::optional<double> update_levels(const DepthUpdate *updates);
};