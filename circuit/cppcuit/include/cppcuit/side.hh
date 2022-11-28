#pragma once

enum class Side { Buy = 0, Sell = 1 };

template <class T> bool deeper(Side side, T a, T b) {
  if (side == Side::Buy) {
    return a < b;
  } else {
    return a > b;
  }
}

template <class T> T deepest(Side side, T a, T b) {
  return deeper(side, a, b) ? a : b;
}

template <class T> bool more_aggressive(Side side, T a, T b) {
  if (side == Side::Buy) {
    return a > b;
  } else {
    return a < b;
  }
}

template <class T> T most_aggressive(Side side, T a, T b) {
  return more_aggressive(side, a, b) ? a : b;
}