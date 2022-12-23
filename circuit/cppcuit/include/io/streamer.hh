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

  bool add_more_data();

public:

  std::size_t read_bytes(char *into, std::size_t max_bytes) override;

  Streamer(std::unique_ptr<ByteReader>);
  ~Streamer();
};