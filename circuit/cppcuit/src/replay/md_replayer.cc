#include "replay/md_replayer.hh"

#include "io/zlib_streamer.hh"

#include <sstream>

namespace {

const char *name_from_category(MdCategory category) {
  switch (category) {
  case MdCategory::Depth:
    return "depth";
  case MdCategory::Trade:
    return "trade";
  }
}

std::string name_for_stream(const MarketStreamConfig &config,
                            const std::string &date) {
  std::stringstream stream;
  stream << config.exchange << "_" << name_from_category(config.category) << "_"
         << config.symbol << "_" << date << ".md.gz";
  return stream.str();
}

Streamer zlib_from_filename(const std::string &filename) {
  Streamer stream{std::make_unique<ZlibReader>(filename)};
  stream.fetch_up_to(1024 * 1024);
  return std::move(stream);
}

} // namespace