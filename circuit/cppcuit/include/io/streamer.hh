#pragma once

#include <cstddef>

#include <memory>
#include <vector>

class ByteReader {
public:
  virtual std::size_t read_bytes(char *into, std::size_t max_bytes) = 0;
  virtual ~ByteReader() = 0;
};

class Streamer final : public ByteReader {
  std::size_t read_to_idx;
  std::vector<char> buffer;
  std::unique_ptr<ByteReader> reader;

  bool initialize_data(std::size_t initialize_up_to);
  bool add_more_data();
  bool readjust_size(std::size_t initial_size, std::size_t added);

public:
  std::size_t read_bytes(char *into, std::size_t max_bytes) override;

  void fetch_up_to(std::size_t max_bytes);
  std::size_t available() const { return buffer.size() - read_to_idx; }

  void ensure_available(std::size_t desired) {
    if (available() < desired) {
      add_more_data();

      if (available() < desired) {
        throw std::runtime_error("Could not ensure enough data was available");
      }
    }
  }

  const char *data() const { return buffer.data() + read_to_idx; }

  void commit(std::size_t bytes) {
    if (buffer.size() - read_to_idx < bytes) {
      throw std::runtime_error("Overflow committing bytes in streamer");
    }

    read_to_idx += bytes;
  }

  Streamer(std::unique_ptr<ByteReader>);
  ~Streamer();
};