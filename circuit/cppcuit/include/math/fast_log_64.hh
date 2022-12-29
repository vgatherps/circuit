#define _USE_MATH_DEFINES

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <stdexcept>

// Here is a tradeoff between accuracy and cache usage
constexpr static std::size_t LOG_CACHE_BITS = 5;

// Reference:
// https://en.wikipedia.org/wiki/Double-precision_floating-point_format The ieee
// representation of a floating point value is:
// * neeeeeeeeeeemmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm
// * one sign bit, n
// * 11 exponent bits, e
// * 52 mantissa bits, m
// which computes (-1)^n * (1.m51_m50_m49...m_1_m_0) * 2^(a - 1023) [1.... is a
// binary fraction]. We can ignore negative numbers here since they're invalid
// for log

// Consider log2(x) (easy to convert to ln with a simple multiplication of
// 1/log2(e)) log2(x) = log2(1.m51_m50_m49...m1_m0) = log2(2^(a - 1023)) log2(x)
// = log2(1.m51...m0) + a - 1023
//
// Only issue now is to compute log2(1.m51...m0)
// Maintain a cache to do linear interpolation

// A final optimization -
// the final term looks like ln(2) * (exponent + (slope * mantissa) + intercept)
// by writing this as ln(2) * (exponent + (slope * mantissa)) + ln(2)*intercept
// or ln(2) * exponenent + ([slope*ln(2)] * mantissa + ln(2) * intercept)
// we can reduce to just two fused-multiply-add instructions
// AND we move the integer conversion of exponent to the end
// of the dependency chain
// fma(
//   ln(2),
//   exponent,
//   fma(slope*ln(2), mantissa, intercept*(ln2))
// )

struct LogLookup {
  double slope;
  double intercept;
};

extern LogLookup tangents[1 << LOG_CACHE_BITS];

double fast_ln(double x) {
  constexpr std::size_t double_mantissa_bits = 52;
  constexpr std::size_t double_exp_bits = 11;
  constexpr std::int64_t exp_nan = 0x7ff;

  std::int64_t x_bits;

  static_assert(sizeof(x_bits) == sizeof(x), "double has 8 bits");
  std::memcpy(&x_bits, &x, sizeof(x));

  // this can be signed - we already ensure the exponent is positive
  // in a later check
  std::int64_t exp_bits = x_bits >> double_mantissa_bits;
  std::int64_t mantissa_bits = x_bits & (((std::int64_t)1 << double_mantissa_bits) - 1);

  // check validity

  if (x_bits < 0) [[unlikely]] {
      return std::numeric_limits<double>::quiet_NaN();
  } else if (exp_bits == double_exp_bits) [[unlikely]] {
    if (std::isinf(x)) {
      return std::numeric_limits<double>::quiet_NaN();
    } else{
      return std::numeric_limits<double>::infinity();
    }
  } else if (exp_bits == 0) [[unlikely]]{
    // zero or subnormal
      return -std::numeric_limits<double>::infinity();
  }

  std::int64_t adjusted_exp = exp_bits - 1023;

  std::int64_t bucket = mantissa_bits >> (double_mantissa_bits - LOG_CACHE_BITS);

  std::int64_t just_mantissa_double_bits = ((std::int64_t)1023 << double_mantissa_bits) | mantissa_bits;

  const LogLookup &adjusted_tangent_line = tangents[bucket];

  double just_mantissa;
  memcpy(&just_mantissa, &just_mantissa_double_bits, sizeof(just_mantissa_double_bits));

  // todo portable fma intrinsics, don't trust compiler
  double sloped_mantissa = (adjusted_tangent_line.slope * just_mantissa) + adjusted_tangent_line.intercept;

  return (M_LN2 * (double)adjusted_exp) + sloped_mantissa;
}