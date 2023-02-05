cmake_minimum_required(VERSION 3.13.0)
set(CMAKE_CXX_STANDARD 20)

if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS 13)
        message(FATAL_ERROR "GCC version must be at least 13!")
    endif()
elseif ("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS 14)
        message(FATAL_ERROR "Clang version must be at least 14!")
    endif()
else()
    message(WARNING "You are using an unsupported compiler! Compilation has only been tested with Clang and GCC.")
endif()

project(cppcuit VERSION 0.1.0)
add_library(cppcuit_lib "")

include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

set(JSON_MultipleHeaders ON)
FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.2/json.tar.xz)
FetchContent_MakeAvailable(json)

find_package( ZLIB REQUIRED )
if ( ZLIB_FOUND )
    include_directories( ${ZLIB_INCLUDE_DIRS} )
    target_link_libraries(cppcuit_lib ${ZLIB_LIBRARIES} )
endif( ZLIB_FOUND )

# Add FlatBuffers directly to our build. This defines the `flatbuffers` target.
add_subdirectory(submodules/flatbuffers
                 ${CMAKE_CURRENT_BINARY_DIR}/flatbuffers-build
                 EXCLUDE_FROM_ALL)

# Process Abseil's CMake build system
add_subdirectory(submodules/abseil-cpp)
 
# Now simply link against flatbuffers as needed to your already declared target.
# The flatbuffers target carry header search path automatically if CMake > 2.8.11.
target_link_libraries(cppcuit_lib flatbuffers)
target_link_libraries(cppcuit_lib nlohmann_json::nlohmann_json)

find_package(Arrow REQUIRED)
target_link_libraries(cppcuit_lib Arrow::arrow_shared)

find_package(Parquet REQUIRED)
target_link_libraries(cppcuit_lib Parquet::parquet_shared)

include(CTest)

include(CPack)

enable_testing()


target_include_directories(cppcuit_lib PUBLIC include submodules/abseil-cpp submodules/scelta/include codegen/)

set(CODEGEN_TARGET_NAME cppcuit_lib)

add_subdirectory(codegen/trade_pressure)
add_subdirectory(src)
add_subdirectory(bin)
add_subdirectory(include)
add_subdirectory(tests)
add_subdirectory(generated_tests)


set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})