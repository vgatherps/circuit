#include <cmath>
#include <cstdint>

std::uint32_t fast_exp_U[256];

// 32 bit version of the fast exp, less accurate but with
// half-sized tables
//
// TODOs:
// 1. Compare to schraudolf method, and modified schraudolf (e^.5x / e^-.5x)
//  a. these might be single-computation slower but trivially vectorizeable
//  b. accuracy between the two is uncertain
//  c. Schraudolf is basically realising that you can take this method,
//     specifically thepart where we project the upper 8 bits into the exponent,
//     and VERY cheaply approximate e^x by converting to int and shifting
//     updates basically since you get the exponent you want in the mantissa,
//     and remaining bits linearly interpolate between the two. I think this one
//     is more accurate and will almost certainly be faster then the schraudolf
//     version where you compute two sides and do a division... You can also do
//     this approximation for any base, including two

// VERY fast way to compute a^b, where 0 <= a <= a, and b >= 0
//
// This is done by computing powers of 2^[1/0x100], and breaking it up into:
// 1. Powers of two
// 2. Powers of 2^1/0x100

// First, for any 16-bit X, we consider the following computation:
//
// 1. split X into {lower: 8, exp: 8}
//   a. X = (exp << 8) + lower
//   b. X = 0x_exp_00 + lower, more conveniently
// 2. consider 2^[1/0x100]^X
//   a. 2^[1/0x100]^X
//   b. 2^[1/0x100]^(0x_exp_lower)
//   c. 2^[1/0x100]^0x_exp_00 * 2^[1/0x100]^0x_lower
//   d. 2^[0x_exp_00/0x100] * 2^[0x_lower/0x100]
//   e. 2^[0x_exp_/0x1] * 2^[0x_lower/0x100]
//   e. 2^[0x_exp_/0x1] * 2^[0x_lower/0x100]

// We now just have to be able to compute the various pwers that we want!
// Computing outright powers of two is very easy.
// For the smaller powers, we can use lookup tables since the space is only 256
// values

// However, how do we quickly convert this back into something useful?
// Reference:
// https://en.wikipedia.org/wiki/Double-precision_floating-point_format The ieee
// representation of a 32-bit floating point value is:
// * neeeeeeeeeeemmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm
// * one sign bit, n
// * 8 exponent bits, e
// * 23 mantissa bits, m
// which computes (-1)^n * (1.m23_m22_m21...m_1_m_0) * 2^(a - 127) [1.... is a
// binary fraction]
//
// As a final optimization, we want to replace on multiplication with an integer
// addition We first consider than an addition in integer space is equal to an
// exponentiation in floating point space and since we have a power of two, we
// can take advantage of this If we consider another representation of
// multiplying the two values: 0(ax8)(mx23) for the middle value,
// 2^[0x_lower/0x100] (fx9)(0x23) for the plain power of two, 2^0x_exp
//
// where a is 127 binary, M is the fractional part of 2^[0x_lower/0x100],
// and f is the exponent of two (here, exp)
//
// This works because:
// 1. 2^[0x_upper/0x100] is positive
// 2. 1 < 2^[0x_upper/0x100] < 2, implying the exponent is equal to 127
// 3. Adding to the exponent is equal to multiplying by an integer power of two,
// which we are.

// We certainly want to make this work with an arbitrary base, as 2^1/0x100 is
// somewhat useless For some multiplier, base ^ exp == [2^1/0x100] ^ (multiplier
// * exp) setting multipler to 0x100 * ln(base) / log(2), you can directly
// compute an equality to base ^ exp

// With this multiplier, we discretize the output.
// That gives about 90k values between two integers in the original space

// I don't see anything that could do a better

// Vectorization seems nigh impossible since you have to gather scatter,
// play endless games with the bit shuffling, and that's not fast any any cpus
// yet.
struct FastExpCache32 {
  float multiplier;
  std::uint32_t max_bits;

  double compute(float x) {

    throw "This is incorrect and I haven't bothered since fast_exp_64 is good "
          "enough";
    union Bits {
      float f;
      std::uint32_t u;
    };
    Bits b;
    b.f = x;
    std::uint32_t bits = b.u;

    // Fast path back to zero
    // I'd really love for this to start all computations after and avoid
    // hoisting them to later, but don't know how to do so without
    // causing other compiler problems...
    if (bits == 0) [[unlikely]] {
      return 1.0;
    }

    if (bits <= this->max_bits) [[likely]] {

      // Project into 2^[1/0x10000] space
      double real_exp = x * this->multiplier;

      struct Splitter {
        std::uint8_t lower;
        std::uint8_t exp;
      };

      union External {
        std::int16_t as_int;
        Splitter split;
      };

      // Discretize to 32 bits
      std::uint16_t as_int = real_exp;

      External ext;

      // Split this integer into pieces
      ext.as_int = as_int;

      std::uint8_t lower_index = ext.split.lower;
      std::int8_t exp = ext.split.exp;

      // Move the exponent back into the mantissa
      std::int32_t fully_upper = (((std::int32_t)exp) << 23);

      // COmbine with the second largest exponential
      std::int32_t combined = fully_upper + fast_exp_U[lower_index];

      Bits back_to_double;
      back_to_double.u = combined;

      // Perform the final multiplication
      return back_to_double.f;
    }

    if (x <= 0.0) {
      return 0.0;
    }

    return NAN;
  }
};

double do_compute(FastExpCache32 &a, float d) { return a.compute(d); }