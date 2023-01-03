#pragma once

#include <concepts>
#include <variant>

#include "io/streamer.hh"
#include "replay/collator.hh"

struct TradeUpdate;
struct DepthUpdate;

using MdMessageType = std::variant<const TradeUpdate *, const DepthUpdate *>;

template <class K> struct MdMessage {
  std::uint64_t local_timestamp_ns;
  MdMessageType update;
  K key;
};

template <class T>
concept md_streamer =
    requires(const char *a, std::size_t l) {
      {
        T::load(a, l)
        } -> std::same_as<std::tuple<std::uint64_t, MdMessageType>>;
    };

class MdStreamReaderBase {
  Streamer streamer;
  std::size_t should_commit;

protected:
  const char *prepare_next_message();
};

template <md_streamer T, std::copyable K>
class MdStreamReader final : public CollatorSource<MdMessage<K>>,
                             public MdStreamReaderBase {
  K key;

public:
  std::optional<MdMessage<K>> next_element() {

    const char *message_data = prepare_next_message();
    if (message_data == nullptr) {
      return {};
    }
    auto [local_timestamp_ns, data] = T::load(message_data);

    return MdMessage<K>{
        .local_timestamp_ns = local_timestamp_ns, .update = data, .key = key};
  }
};

class TradeMessageConverter {
public:
  static std::tuple<std::uint64_t, MdMessageType> load(const char *data,
                                                       std::size_t length);
};

class DepthMessageConverter {
public:
  static std::tuple<std::uint64_t, MdMessageType> load(const char *data,
                                                       std::size_t length);
};

using TidCollator = Collator<MdMessage<std::uint32_t>>;