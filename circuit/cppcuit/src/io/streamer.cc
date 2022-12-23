#include "io/streamer.hh"

#include <cassert>
#include <cstring>

bool Streamer::add_more_data() {
  if (!reader) {
    return false;
  }
  assert(read_to_idx <= buffer.size());
  std::size_t remaining = buffer.size() - read_to_idx;

  if (read_to_idx != 0) {
    if (read_to_idx > buffer.size() / 2) {
      buffer.resize(1 + buffer.size() * 2);
    }
    std::memmove(buffer.data(), buffer.data() + read_to_idx, remaining);
    read_to_idx = 0;
  }

  std::size_t bytes_added =
      reader->read_bytes(buffer.data() + remaining, buffer.size() - remaining);

  if (bytes_added == 0) {
    reader.reset();
    return false;
  } else {
    buffer.resize(remaining + bytes_added);
    return true;
  }
}


std::size_t Streamer::read_bytes(char *into, std::size_t max_bytes) {
    if (read_to_idx < buffer.size()) {
        std::size_t remaining = buffer.size() - read_to_idx;
        std::size_t to_copy = remaining > max_bytes ? max_bytes : remaining;
        std::memcpy(into, buffer.data() + remaining, to_copy);
        read_to_idx += to_copy;
        return to_copy;
    }

    if (add_more_data()) {
        return this->read_bytes(into, max_bytes);
    }

    return 0;
}

Streamer::Streamer(std::unique_ptr<ByteReader> reader)
    : read_to_idx(0), buffer(), reader(std::move(reader)) {}

Streamer::~Streamer() {}