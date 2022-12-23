#pragma once

#include "io/streamer.hh"
#include <zlib.h>

class ZlibReader final : public ByteReader {
  gzFile file;

public:
  std::size_t read_bytes(char *into, std::size_t max_bytes) override;

  ZlibReader(const std::string &filename);
  ~ZlibReader();
};