#include <cstdint>
#include <cmath>

double fast_exp_L[256];
std::uint64_t fast_exp_U[256];

// VERY fast way to compute a^b, where 0 <= a <= a, and b >= 0
//
// This is done by computing powers of 2^[1/0x10000], and breaking it up into:
// 1. Powers of two
// 2. Powers of 2^1/0x100
// 3. Powers of 2^1/0x10000

// First, for any 32-bit X, we consider the following computation:
//
// 1. split X into {lower: 8, upper: 8, exp: 16}
//   a. X = (exp << 16) + (upper << 8) + lower
//   b. X = 0x_exp_0000 + 0x_upper_00 + lower, more conveniently
// 2. consider 2^[1/0x10000]^X
//   a. 2^[1/0x10000]^X
//   b. 2^[1/0x10000]^(0x_exp_upper_lower)
//   c. 2^[1/0x10000]^0x_exp_0000 * 2^[1/0x10000]^0x_upper_00 * 2^[1/0x10000]^0x_lower
//   d. 2^[0x_exp_0000/0x10000] * 2^[0x_upper_00/0x10000] * 2^[0x_lower/0x10000]
//   e. 2^[0x_exp_/0x1] * 2^[0x_upper/0x100] * 2^[0x_lower/0x10000]
//   e. 2^[0x_exp_/0x1] * 2^[0x_upper/0x100] * 2^[0x_lower/0x10000]

// We now just have to be able to compute the various pwers that we want!
// Computing outright powers of two is very easy.
// For the smaller powers, we can use lookup tables since the space is only 256 values

// However, how do we quickly convert this back into something useful?
// Reference: https://en.wikipedia.org/wiki/Double-precision_floating-point_format
// The ieee representation of a floating point value is:
// * neeeeeeeeeeemmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm
// * one sign bit, n
// * 11 exponent bits, e
// * 52 mantissa bits, m
// which computes (-1)^n * (1.m51_m50_m49...m_1_m_0) * 2^(a - 1023) [1.... is a binary fraction]
//
// As a final optimization, we want to replace on multiplication with an integer addition
// We first consider than an addition in integer space is equal to an exponentiation in floating point space
// and since we have a power of two, we can take advantage of this
// If we consider another representation of multiplying the upper two values:
// 0(ax11)(mx52) for the middle value, 2^[0x_upper/0x100]
// (fx12)(0x52) for the plain power of two, 2^0x_exp
//
// where a is 1023 in binary, M is the fractional part of 2^[0x_upper/0x100],
// and f is the exponent of two (here, exp)
//
// This works because:
// 1. 2^[0x_upper/0x100] is positive
// 2. 1 < 2^[0x_upper/0x100] < 2, implying the exponent is equal to 1023
// 3. Adding to the exponent is equal to multiplying by an integer power of two, which we are.

// We certainly want to make this work with an arbitrary base, as 2^1/0x10000 is somewhat useless
// For some multiplier,
// base ^ exp == [2^1/0x10000] ^ (multiplier * exp)
// setting multipler to 0x10000 ln(base) / log(2),
// you can directly compute an equality to base ^ exp

// With this multiplier, we discretize the output.
// That gives about 90k values between two integers in the original space

struct FastExpCache {
    double multiplier;
    std::uint64_t max_bits;

    double compute(double x) {

        union Bits {
            double d;
            std::uint64_t u;
        };
        Bits b;
        b.d = x;
        std::uint64_t bits = b.u;

        
        // Fast path back to zero
        // I'd really low for this to start all computations after and avoid
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
                std::uint8_t upper;
                std::int16_t exp;
            };

            union External {
                std::int32_t as_int;
                Splitter split;
            };


            // Discretize to 32 bits
            std::int32_t as_int = real_exp;

            External ext;

            // Split this integer into pieces
            ext.as_int = as_int;

            std::uint8_t lower_index = ext.split.lower;
            std::uint8_t upper_index = ext.split.upper;
            std::int16_t exp = ext.split.exp;

            // Move the exponent back into the mantissa
            std::int64_t fully_upper = (((std::int64_t)exp) << 52);

            // COmbine with the second largest exponential
            std::int64_t combined = fully_upper + fast_exp_U[upper_index];

            Bits back_to_double;
            back_to_double.u = combined;

            // Perform the final multiplication
            return fast_exp_L[lower_index] * back_to_double.d;
        }


        if (x <= 0.0) {
            return 0.0;
        }

        return NAN;
    }
};

double do_compute(FastExpCache &a, double d) {
    return a.compute(d);
}