#include "replay/md_source.hh"
#include "cppcuit/runtime_error.hh"
#include "md_types/depth_message_generated.h"
#include "md_types/single_trade_message_generated.h"
std::tuple<const char *, std::size_t>
MdStreamReaderBase::prepare_next_message() {
  if (!streamer.has_data()) {
    return {nullptr, 0};
  }

  streamer.commit(should_commit);

  streamer.ensure_available(4);
  const char *length_data = streamer.data();

  std::uint32_t length;
  static_assert(sizeof(length) == 4);
  memcpy(&length, length_data, sizeof(length));

  streamer.commit(sizeof(length));

  should_commit = length;

  streamer.ensure_available(length);
  return {streamer.data(), length};
}

template <class M, class V, class L>
  requires requires(L l, const void *m) {
             { l(m) } -> std::same_as<const M *>;
           }
std::tuple<std::uint64_t, MdMessageType>
do_load(const char *data, std::size_t length, const V &ver_fn,
        const L &load_fn) {
  // Verification overhead appears to be really tiny.
  // It's easy to downsample if the overhead gets too high

  flatbuffers::Verifier ver((const std::uint8_t *)data, length);
  bool ok = ver_fn(ver);

  if (!ok) [[unlikely]] {
    cold_runtime_error("Message could not be verified");
  }

  const M *message = load_fn((const void *)data);
  return {(std::uint64_t)message->local_time_us() * 1000, message->message()};
}

std::tuple<std::uint64_t, MdMessageType>
SingleTradeConverter::load(const char *data, std::size_t length) {
  return do_load<SingleTradeMessage>(data, length, VerifySingleTradeMessageBuffer,
                                     GetSingleTradeMessage);
}

std::tuple<std::uint64_t, MdMessageType>
DepthMessageConverter::load(const char *data, std::size_t length) {
  return do_load<DepthMessage>(data, length, VerifyDepthMessageBuffer,
                               GetDepthMessage);
}