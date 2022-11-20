#pragma GCC target("avx")
#pragma GCC target("bmi")

#include <immintrin.h>
#include <smmintrin.h>
#include <cstdint>
#include <array>

// TODO store side by side?
// if we make each one take up the same space, we save an instruction?
__m128i dot_shuffle_control[16];
__m128i length_shift_control[16];
__m128i length_mask[16];

__attribute__((cold, noreturn, noinline)) static void bail_on_bad_integer()
{
    throw "blah";
}

struct CondensedDecimal
{
    // The original string, with the decimal point removed,
    // shifted so that it ends on the final byte and is prefixed with zeros
    //
    // so 1234.13432 followed by garbage would become
    // 0000000123413432
    // dot at original index 4
    // original length 10
    std::int64_t int_value;
    std::uint32_t dot;
    std::uint32_t length;
};

std::int64_t test(__m128i input)
{
    // 1. convert from ASCII '0' .. '9' to numbers 0 .. 9
    const __m128i ascii0 = _mm_set1_epi8('0');
    const __m128i t0 = _mm_sub_epi8(input, ascii0);

    // 2. convert to 2-digit numbers
    const __m128i mul_1_10 = _mm_setr_epi8(10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1);
    const __m128i t1 = _mm_madd_epi16(t0, mul_1_10);

    // 3. convert to 4-digit numbers
    const __m128i mul_1_100 = _mm_setr_epi16(100, 1, 100, 1, 100, 1, 100, 1);
    const __m128i t2 = _mm_madd_epi16(t1, mul_1_100);

    // 4a. convert form 32-bit into 16-bit element vector
    const __m128i t3 = _mm_packus_epi32(t2, t2);

    // 4. convert to 8-digit numbers
    const __m128i mul_1_10000 = _mm_setr_epi16(10000, 1, 10000, 1, 10000, 1, 10000, 1);
    const __m128i t4 = _mm_madd_epi16(t3, mul_1_10000);

    return _mm_cvtsi128_si64(t4) * 100000000 + _mm_extract_epi64(t4, 1);
}

#define arr(T) std::array<T, N>
#define FOR(i) for (int i = 0; i < N; i++)
#define SPLIT_FOR(i) \
    }                \
    FOR(i)           \
    {
constexpr int N = 8;

// TODO do this in terms of pairs of strings

// Takes a series of 15-digit decimal strings aaaa.bbbbb, and converts them into
// 15 digit integers with length and dot position recorded.
void __attribute__((noinline)) condense_string_arr(const __m128i *data, CondensedDecimal *out, bool &is_bad)
{
    // have to mask off via length to avoid spuriosuly finding new dots
    __m128i find_dot = _mm_set1_epi8('.');
    arr(__m128i) cleaned;
    std::uint32_t sans_first_dot = 0;
    // Schedule loads and comparisons of data
    FOR(i)
    {
        // Set the last character to zero. This is used by the shuffles to
        // forward fill leading zeros
        cleaned[i] = _mm_insert_epi8(data[i], '0', 15);
        SPLIT_FOR(i)
        // Project the string down to the far end - this gives us many
        // leading zeros, instead of many trailing zeros
        // The reason that we do this, is because
        cleaned[i] = _mm_shuffle_epi8(cleaned[i], length_shift_control[out[i].length]);
        SPLIT_FOR(i)
        // Locate the dot. This is after shifting to the other end of the array
        // This is also done in the ascii-adjusted space
        __m128i is_eq_dot = _mm_cmpeq_epi8(find_dot, cleaned[i]);
        std::uint32_t = _mm_movemask_epi8(is_eq_dot);
        // aggregate all of the validation masks - discover if there are any bad nonzero masks
        is_bad |= (is_dot & (is_dot - 1)) == 0;
        // schedule discover of the dot index.
        std::uint32_t dot_idx = __tzcnt_u32(is_dot);
        out[i].dot = dot_idx;
        // Shift the dot outside of the array, if it exists
        cleaned[i] = _mm_shuffle_epi8(cleaned[i], dot_shuffle_control[dot_idx]);

        // Now for the conversion into numbers
        SPLIT_FOR(i)
        const __m128i ascii0 = _mm_set1_epi8('0');

        // 1. convert from ASCII '0' .. '9' to numbers 0 .. 9
        cleaned[i] = _mm_sub_epi8(cleaned[i], ascii0);
        SPLIT_FOR(i)
        // 2. convert to 2-digit numbers
        const __m128i mul_1_10 = _mm_setr_epi8(10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1);
        cleaned[i] = _mm_madd_epi16(cleaned[i], mul_1_10);
        SPLIT_FOR(i)
        // 3. convert to 4-digit numbers
        const __m128i mul_1_100 = _mm_setr_epi16(100, 1, 100, 1, 100, 1, 100, 1);
        cleaned[i] = _mm_madd_epi16(cleaned[i], mul_1_100);
        SPLIT_FOR(i)
        // 4a. convert form 32-bit into 16-bit element vector
        cleaned[i] = _mm_packus_epi32(cleaned[i], cleaned[i]);
        SPLIT_FOR(i)
        // 4. convert to 8-digit numbers
        const __m128i mul_1_10000 = _mm_setr_epi16(10000, 1, 10000, 1, 10000, 1, 10000, 1);
        cleaned[i] = _mm_madd_epi16(cleaned[i], mul_1_10000);
        SPLIT_FOR(i)
        out[i].int_value = _mm_cvtsi128_si64(cleaned[i]) * 100000000 + _mm_extract_epi64(cleaned[i], 1);
    }
}