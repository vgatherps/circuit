#include "cppcuit/runtime_error.hh"

#include <stdexcept>

__attribute__ ((noreturn, cold)) void cold_runtime_error(const char *message) {
  throw std::runtime_error(message);
}