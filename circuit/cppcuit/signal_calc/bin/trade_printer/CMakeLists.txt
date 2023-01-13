add_executable(
  local_trade_printer
)

target_sources(local_trade_printer PRIVATE trade_printer.cc)

target_link_libraries(
  local_trade_printer
  cppcuit_lib
  nlohmann_json::nlohmann_json
  absl::flags_usage
  absl::flags_parse
  signal_calc_lib
  pressure
)