add_subdirectory(book_pressure)
add_subdirectory(decay)
add_subdirectory(sampling)
add_subdirectory(trade_pressure)


target_sources(cppcuit_lib PRIVATE parameter.cc)