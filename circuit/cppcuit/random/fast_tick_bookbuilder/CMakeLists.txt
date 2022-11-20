cmake_minimum_required(VERSION 3.1.0)
set(CMAKE_CXX_STANDARD 20)

project(cppcuit VERSION 0.1.0)

include(CTest)
enable_testing()

add_library(cppcuit example.cpp)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
