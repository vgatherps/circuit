add_subdirectory(book_pressure)
add_subdirectory(multi_stream_book)

target_sources(tests PRIVATE test_bookbuilder.cc)