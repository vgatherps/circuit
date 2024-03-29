#pragma once

#include <cstdint>

#include "raw_call.hh"

class RawOutputHandle {
  std::uint32_t offset;
  std::uint32_t valid_offset;

public:
  std::uint32_t get_offset() const { return offset; }
  std::uint32_t get_valid_offset() const { return valid_offset; }

  RawOutputHandle(std::uint32_t offset, std::uint32_t valid_offset)
      : offset(offset), valid_offset(valid_offset) {}
};

template <class T> class OutputHandle : public RawOutputHandle {
public:
  OutputHandle(RawOutputHandle h)
      : RawOutputHandle(h.get_offset(), h.get_valid_offset()) {}
};

class Circuit;
template <class T>
using CircuitCall = void (*)(Circuit *, std::uint64_t, T,
                             RawCall<const Circuit *>);