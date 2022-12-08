cmake_minimum_required(VERSION 3.13.0)
set(CMAKE_CXX_STANDARD 20)

project(cppcuit VERSION 0.1.0)

include(CTest)
include(FetchContent)
include(CPack)

enable_testing()

include_directories(include)

add_subdirectory(src)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})

set(JSON_MultipleHeaders ON)

FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz)
FetchContent_MakeAvailable(json)

target_link_libraries(cppcuit_lib json)