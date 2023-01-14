enable_testing()

add_executable(
  tests
)

target_link_libraries(
  tests
  PRIVATE
  GTest::gtest_main
  cppcuit_lib
)

target_compile_options(tests PUBLIC -fsanitize=undefined)
target_link_options(tests PUBLIC -fsanitize=undefined)

add_subdirectory(io)
add_subdirectory(math)
add_subdirectory(replay)
add_subdirectory(signals)

include(GoogleTest)
gtest_discover_tests(tests)