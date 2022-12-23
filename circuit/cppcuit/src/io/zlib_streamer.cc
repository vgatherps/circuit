#include "io/zlib_streamer.hh"

#include <string>

std::size_t ZlibReader::read_bytes(char *into, std::size_t max_bytes) {
  int num_read = gzread(file, into, max_bytes);

  if (num_read >= 0) {
    return num_read;
  }

  std::string error_msg = "Failed to read from gzip file with error ";
  throw std::runtime_error(error_msg + gzerror(file, &num_read));
}

ZlibReader::ZlibReader(const std::string &filename) {
  const char *file_ptr = filename.c_str();

  file = gzopen(file_ptr, "rb");

  if (file == nullptr) {
    std::string error_msg = "Failed to open gzip file " + filename;
    throw std::runtime_error(error_msg);
  }
}

ZlibReader::~ZlibReader() { gzclose(file); }