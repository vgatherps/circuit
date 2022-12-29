#pragma once

#include "signals/bookbuilder.hh"

class BookImpulseTracker {
  BookBuilder<double, double> book;

public:
  void update_levels(const DepthUpdate *updates);
};