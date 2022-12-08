cmake_minimum_required(VERSION 3.13.0)
set(CMAKE_CXX_STANDARD 20)

project(trade_pressure_signal VERSION 0.1.0)

include(CTest)
include(FetchContent)
set(JSON_MultipleHeaders ON)
FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz)
FetchContent_MakeAvailable(json)

enable_testing()

add_subdirectory(cppcuit cppcuit/build/src)

include_directories(include)
include_directories(codegen)

add_library(trade_pressure_lib "")

add_subdirectory(src)
add_subdirectory(codegen/trade_pressure)

target_link_libraries(trade_pressure_lib cppcuit_lib)
target_link_libraries(trade_pressure_lib pressure_lib)
target_link_libraries(trade_pressure_lib json)
