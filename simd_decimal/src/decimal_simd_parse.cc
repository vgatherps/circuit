#include "decimal_simd_parse.hh"

__m128i dot_shuffle_control[16];
__m128i length_shift_control[16];

static __m128i generate_dot_for(int dot) {
  // we're compressing everything towards the end
  // 'after' the dot, in raw index order, we do nothing
  // before / at the dot, we shift over from the index ahead
  // the 0th index is always in-place, as this one should *always* be zero
  std::int8_t data[16] = {0};
  for (int i = 0; i < 16; i++) {
    if (i > dot || i == 0) {
      data[i] = i;
    } else {
      data[i] = i - 1;
    }
  }

  return _mm_loadu_si128((__m128i *)&data);
}

static int generate_dot_shuffle_control() {
  for (int i = 0; i < 16; i++) {
    dot_shuffle_control[i] = generate_dot_for(i);
  }

  return 0;
}

static __m128i generate_length_shift_for(int length) {
  // We compress eveything to the very end, while assuming that
  // the last element is zero. This lets us shift AND mask all in one go
  // basically, we compress by (16 - length)
  std::int8_t data[16] = {0};
  int shift_up_front = 16 - length;

  // fill up the front part of the array to select from known zeros
  for (int i = 0; i < shift_up_front; i++) {
    data[i] = 15;
  }

  // Fill the later parts of the array to select from the front
  for (int i = 0; i < length; i++) {
    data[i + shift_up_front] = i;
  }

  return _mm_loadu_si128((__m128i *)&data);
}

static int generate_length_shift_control() {
  for (int i = 0; i < 16; i++) {
    length_shift_control[i] = generate_length_shift_for(i);
  }

  return 0;
}

int _DOT_CONTROL_MARKER___ = generate_dot_shuffle_control();
int _LENGTH_SHIFT_MARKER___ = generate_length_shift_control();

__attribute__((cold, noreturn, noinline)) void bail_on_bad_integer() {
  throw "blah";
}
