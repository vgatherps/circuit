#pragma once

#include <concepts>
#include <functional>

#include "cppcuit/circuit.hh"
#include "cppcuit/runtime_error.hh"
#include "io/streamer.hh"
#include "replay/collator.hh"

#include "md_types/trade_message_generated.h"

#include <variant>

using MdMessageType = std::variant<const TradeUpdate *>;

template <class K> struct MdMessage {
  std::uint64_t local_timestamp_ns;
  MdMessageType update;
  K key;
};

template <class T>
concept md_streamer =
    requires(const char *a, std::size_t l) {
      { T::load(a, l) } -> std::same_as<std::tuple<std::uint64_t, MdMessageType>>;
    };

template <md_streamer T, std::copyable K>
class MdStreamReader : public CollatorSource<MdMessage<K>> {

  Streamer streamer;
  std::size_t should_commit;
  K key;

public:
  std::optional<MdMessage<K>> next_element() {
    if (!streamer.has_data()) {
      return {};
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
    const char *message_data = streamer.data();

    auto [local_timestamp_ns, data] = T::load(message_data);

    return MdMessage<K> {
      .local_timestamp_ns = local_timestamp_ns, .update = data, .key = key
    }
  }
};

class TradeMessageConverter {
public:
  std::tuple<std::uint64_t, MdMessageType> load(const char *data, std::size_t length) {
    
    // Verification overhead appears to be really tiny.
    // It's easy to downsample if the overhead gets too high

    flatbuffers::Verifier ver((const std::uint8_t *)data, length);
    bool ok = VerifyTradeMessageBuffer(ver);

    if (!ok) [[unlikely]] {
        cold_runtime_error("Trade Message could not be verified");
    }

    const TradeMessage *message = GetTradeMessage((const void *)data);
    return {(std::uint64_t)message->local_time_us() * 1000, message->message()};
  }
};