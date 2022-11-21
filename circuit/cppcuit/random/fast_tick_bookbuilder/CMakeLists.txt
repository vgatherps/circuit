cmake_minimum_required(VERSION 3.1.0)
set(CMAKE_CXX_STANDARD 20)

project(fast_tick_bookbuilder VERSION 0.1.0)

include(CTest)
enable_testing()

add_library(cppcuit bookbuilder.cc)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
