#include <cassert>
#include <cmath>
#include <stdexcept>

#include "math/fast_log_64.hh"

constexpr static std::size_t TANGENTS = 1 << LOG_CACHE_BITS;

// TODO consider some sort of spline solution if this ever gets used for real
// I expect you could drastically shrink the tangent space by doing so

namespace _fast_log_detail {
LogLookup _fast_log_tangents[TANGENTS];
}

using namespace _fast_log_detail;

static int precompute_log_tangents() {
  double step_size = 1.0 / TANGENTS;
  for (std::size_t i = 0; i < TANGENTS; i++) {

    // Two options for finding best fit line:
    // 1. Interpolate between log2(x) and log2(x+step_size)
    //   This gives continuity at the edges, and ensures the result is zero at
    //   one
    // 2. Use many points to get a true best-fit line.
    //    This is more accurate but sacrifices continuity at the points and zero
    //    at one
    //
    // I go with one as accuracy is improved by a larger set of lines, and
    // continuity as well as zero-at-one is very valuable

    // I feel like best way is to actually fit a linear regression
    double x = 1.0 + step_size * i;
    double x_next = x + step_size;
    double log2_x = std::log2(x);
    double log2_x_next = std::log2(x_next);

    // slope is y_diff / x_diff
    double slope = (log2_x_next - log2_x) / step_size;

    // intercept is y - slope*x, such that intercept + slope * x = y
    double intercept = log2_x - slope * x;

    // Finally, we store these pre-multiplied by ln(2) as that makes it
    // possily to optimize the actual log calculation quite a bit

    _fast_log_tangents[i].slope = slope * M_LN2;
    _fast_log_tangents[i].intercept = intercept * M_LN2;
  }

  return 1;
}

int _fast_ln_fill = precompute_log_tangents();

double fast_ln_out_of_line(double x) { return fast_ln(x); }