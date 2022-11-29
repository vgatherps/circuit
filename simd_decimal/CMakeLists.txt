cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 20)

project(decimal_simd VERSION 0.1.0)

include(CTest)
enable_testing()

include_directories(include)
add_subdirectory(lib/googletest)
add_subdirectory(test)
add_subdirectory(src)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
