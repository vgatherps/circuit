#include <immintrin.h>
#include <cstdint>
#include <array>;

// TODO store side by side?
// if we make each one take up the same space, we save an instruction?
__m128i dot_shuffle_control[16];
__m128i shift_to_end_control[16];
__mmask16 dot_merge_masks[16];
__mmask16 shift_to_end_masks[16];

const static __m128i find_dot = _mm_set1_epi8('.');
const static __m128i ascii0 = _mm_set1_epi8('0');
const static __m128i mul_1_10 = _mm_setr_epi8(10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1, 10, 1);

__attribute__((cold, noreturn)) void bail_on_bad_integer();

#define arr(T) std::array<T, N>

constexpr int N = 8;

// the shuffle-and-mask is *slightly* slower than an outright shift, but it means we don't need to
// make a compile time decision here, it's vastly better for batching in that sense
// clangs optimizes this VASTLY better than gcc
void parse_from_simd(const arr(__m128i) & strings, const arr(unsigned int) & alength, arr(std::int64_t) & out)
{

    // so potential issue here, this again forces an extra multiply by 10?
    // realistically I think this means that we have to cut length.
    // it sort of sucks since it shifts a single dependency above the parallel loads?
    // do we just shove that until the end?
    arr(unsigned int) length = alength;
    arr(__m128i) cleaned;
    arr(std::uint32_t) dot_idx;
    for (int i = 0; i < N; i++)
    {
        std::uint32_t is_dot = _mm_movemask_epi8(_mm_cmpeq_epi8(find_dot, strings[i]));
        std::uint32_t num_dots = __builtin_popcount(is_dot);
        if (num_dots > 1)
        {
            bail_on_bad_integer();
        }
        length[i] -= num_dots;
        // there's a sort of pointless instruction getting added here
        // because compiler is trying to us ax instead of eax
        dot_idx[i] = __tzcnt_u32(num_dots);
    }

    for (int i = 0; i < N; i++)
    {
        // might need to get rid of the dot somehow outside of the mask
        // do the two shuffles in parallel and blend later, shrinks dependency chain
        __m128i merged = _mm_mask_shuffle_epi8(strings[i], dot_merge_masks[dot_idx[i]], strings[i], dot_shuffle_control[dot_idx[i]]);
        cleaned[i] = _mm_maskz_shuffle_epi8(
            shift_to_end_masks[dot_idx[i]],
            merged,
            shift_to_end_control[dot_idx[i]]);
        cleaned[i] = merged;
    }

    for (int i = 0; i < N; i++)
    {
        const __m128i t0 = _mm_subs_epu8(cleaned[i], ascii0);

        // 2. convert to 2-digit numbers

        const __m128i t1 = _mm_maddubs_epi16(t0, mul_1_10);

        // 3. convert to 4-digit numbers
        const __m128i mul_1_100 = _mm_setr_epi16(100, 1, 100, 1, 100, 1, 100, 1);
        const __m128i t2 = _mm_madd_epi16(t1, mul_1_100);

        // 4a. convert form 32-bit into 16-bit element vector
        const __m128i t3 = _mm_packus_epi32(t2, t2);

        // 4. convert to 8-digit numbers
        const __m128i mul_1_10000 = _mm_setr_epi16(10000, 1, 10000, 1, 10000, 1, 10000, 1);
        const __m128i t4 = _mm_madd_epi16(t3, mul_1_10000);
        const __m128i t4_top = _mm_unpackhi_epi64(t4, t4);

        std::int64_t bottom = _mm_cvtsi128_si64(t4);
        std::int64_t top = _mm_cvtsi128_si64(t4_top);

        out[i] = (100000000 * bottom) + top;
    }
}