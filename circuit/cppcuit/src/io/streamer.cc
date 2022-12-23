#include "io/streamer.hh"

#ifdef NDEBUG
#undef NDEBUG
#endif

#include <cassert>
#include <cstring>

ByteReader::~ByteReader() {}

constexpr static std::size_t INITIAL_SIZE = 4096;

bool Streamer::initialize_data(std::size_t initialize_up_to) {
  assert(buffer.size() == 0);
  assert(read_to_idx == 0);
  assert(initialize_up_to > 0);

  if (!reader) {
    return false;
  }

  buffer.resize(initialize_up_to);

  std::size_t bytes_read = reader->read_bytes(buffer.data(), initialize_up_to);

  return readjust_size(0, bytes_read);
}

bool Streamer::add_more_data() {
  if (!reader) {
    return false;
  }
  if (buffer.size() == 0) {
    return initialize_data(INITIAL_SIZE);
  }
  assert(read_to_idx <= buffer.size());
  std::size_t remaining = buffer.size() - read_to_idx;

  if (read_to_idx != 0) {
    if (read_to_idx > buffer.size() / 2) {
      buffer.resize(1 + buffer.size() * 2);
    }
    std::memmove(buffer.data(), buffer.data() + read_to_idx, remaining);
    // update afterwards since the extra remaining is just zeros/garbage anyways
    read_to_idx = 0;
  }

  std::size_t bytes_added =
      reader->read_bytes(buffer.data() + remaining, buffer.size() - remaining);

  return readjust_size(remaining, bytes_added);
}

bool Streamer::readjust_size(std::size_t initial_size, std::size_t added) {
  buffer.resize(initial_size + added);
  if (added == 0) {
    reader.reset();
    return false;
  } else {
    return true;
  }
}

void Streamer::fetch_up_to(std::size_t max_bytes) {
  if (max_bytes == 0) {
    return;
  }
  if (buffer.size() == 0) {
    initialize_data(max_bytes);
    return;
  }

  // Refill the buffer and reset initial index to zero
  add_more_data();
  assert(read_to_idx == 0);

  std::size_t initial_size = buffer.size();
  if (initial_size < max_bytes && reader) {
    std::size_t extra_bytes = max_bytes - initial_size;
    buffer.resize(max_bytes);

    std::size_t bytes_added =
        reader->read_bytes(buffer.data() + initial_size, extra_bytes);
    readjust_size(initial_size, bytes_added);
  }
}

std::size_t Streamer::read_bytes(char *into, std::size_t max_bytes) {
  if (read_to_idx < buffer.size()) {
    std::size_t remaining = buffer.size() - read_to_idx;
    std::size_t to_copy = std::min(remaining, max_bytes);
    std::memcpy(into, buffer.data() + read_to_idx, to_copy);
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