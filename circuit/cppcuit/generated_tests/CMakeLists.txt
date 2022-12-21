enable_testing()

add_executable(
  pycircuit_gen_test
)

FetchContent_MakeAvailable(json)
target_link_libraries(
  pycircuit_gen_test
  PRIVATE
  GTest::gtest_main
  cppcuit_lib
  nlohmann_json::nlohmann_json
)

add_subdirectory(codegen)

include(GoogleTest)
gtest_discover_tests(pycircuit_gen_test)