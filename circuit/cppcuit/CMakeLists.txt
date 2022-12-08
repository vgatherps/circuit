cmake_minimum_required(VERSION 3.13.0)
set(CMAKE_CXX_STANDARD 20)

project(cppcuit VERSION 0.1.0)
add_library(cppcuit_lib "")

include(CTest)

include(CPack)

enable_testing()

target_include_directories(cppcuit_lib PUBLIC include)

add_subdirectory(src)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
target_link_libraries(cppcuit_lib json)