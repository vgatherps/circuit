add_executable(
  trade_printer
)

target_sources(trade_printer PRIVATE trade_printer.cc)

target_link_libraries(
  trade_printer
  PRIVATE
  cppcuit_lib
)

target_compile_options(trade_printer PUBLIC -fsanitize=undefined)
target_link_options(trade_printer PUBLIC -fsanitize=undefined)