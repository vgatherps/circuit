#pragma once

#include <span>

struct AnnotatedLevel {
  double price;
  double previous_size;
  double current_size;
};

struct BookLevel {
  double size;
  double price;
};

struct BBO {
  BookLevel bid, ask;
};

struct UpdatedLevels {
  std::span<AnnotatedLevel> bids, asks;
};