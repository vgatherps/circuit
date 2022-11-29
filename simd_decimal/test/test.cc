#include "decimal_simd_parse.hh"

#include "gtest/gtest.h"
#include <iostream>

using namespace std;

TEST(blaTest, test1) {
  const char *number_1 =
      "98765432123.456_.........................................";
  int true_length = 15;

  CondensedDecimal out;
  out.length = true_length;
  bool is_bad = false;

  __m128i loaded = _mm_loadu_si128((__m128i *)number_1);

  condense_string_arr<1>(&loaded, &out, is_bad);

  cout << "int value " << out.int_value << " dot " << out.dot
       << ", is_bad: " << is_bad << endl;
}

int main(int argc, char **argv) {
  ::testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
