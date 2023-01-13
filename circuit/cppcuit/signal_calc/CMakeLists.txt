include_directories(include)
include_directories(codegen)

add_library(signal_calc_lib "")

add_subdirectory(src)
add_subdirectory(bin)
add_subdirectory(codegen/trade_pressure)

target_link_libraries(signal_calc_lib PRIVATE cppcuit_lib)
target_link_libraries(signal_calc_lib PRIVATE pressure)
