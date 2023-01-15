#pragma once

#include <cstdint>

#ifdef __SSE2__
#include <emmintrin.h>
#endif

enum class Side : std::uint8_t { Buy = 0, Sell = 1 };

inline Side other_side(Side s) {
  return (Side)((std::uint8_t)1 - (std::uint8_t)s);
}

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

#ifdef __SSE2__

// Compilers understand how to constant propagate this quite well
// So there's no need for a version that inlines / constant propagates better
inline double flip_sign_if_buy(Side s, double d) {
  static constexpr std::uint64_t flippers[2] = {(std::uint64_t)1 << 63, 0};

  const double *dp = (const double *)&flippers[(std::uint8_t)s];
  __m128d flipper = _mm_load_sd(dp);
  __m128d d_vec = _mm_set_sd(d);

  return _mm_xor_pd(flipper, d_vec)[0];
}

#else
inline double flip_sign_if_buy(Side s, double d) {
  static constexpr double flippers[2] = {-1, 1};
  return d * flippers[(int)s];
}
#endif