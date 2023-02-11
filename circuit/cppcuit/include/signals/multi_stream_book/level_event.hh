#pragma once

#include <optional>
#include <variant>

struct Add {
  double size;
};

struct Cancel {
  double size;
};

struct Take {
  double size;
  double visible_size_on_book;
  std::size_t trade_idx;
};

struct Refresh {
  std::optional<double> size;
};

using LevelEvent = std::variant<Add, Cancel, Take, Refresh>;