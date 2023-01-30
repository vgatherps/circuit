#pragma once

#include <vector>

struct AnnotatedLevel {
  double price;
  double previous_size;
  double current_size;
};

struct BookLevel {
  double price;
  double size;
};

struct BBO {
  BookLevel bid, ask;

  double mid() const { return 0.5 * (bid.price + ask.price); }
};

struct UpdatedLevels {
  std::vector<AnnotatedLevel> bids, asks;
};