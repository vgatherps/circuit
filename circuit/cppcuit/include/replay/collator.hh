#pragma once

#include <compare>
#include <concepts>
#include <cstdint>
#include <optional>
#include <vector>

#include "cppcuit/signal_requirements.hh"
#include "replay/inplace_queue.hh"

template <class T>
  requires HAS_FIELD(T, std::uint64_t, local_timestamp_ns)
std::uint64_t get_local_timestamp(const T &t) {
  return t.local_timestamp_ns;
}

template <class T>
  requires HAS_FIELD(T, std::uint64_t, local_timestamp_ns)
std::uint64_t get_local_timestamp(const T *t) {
  return t->local_timestamp_ns;
}

template <class T> std::uint64_t get_local_timestamp(const T &t);

template <class T>
concept has_local_timestamp = requires(const T &a) {
                                {
                                  get_local_timestamp(a)
                                  } -> std::same_as<std::uint64_t>;
                              };

template <has_local_timestamp T> class CollatorSource {
public:
  virtual std::optional<T> next_element() = 0;

  virtual ~CollatorSource() {}
};

template <has_local_timestamp T>
  requires std::movable<T>
class Collator final : public CollatorSource<T> {

  struct PendingElement {
    T data;
    std::unique_ptr<CollatorSource<T>> source;

    std::uint64_t get_pending_timestamp() const {
      return get_local_timestamp(data);
    }

    std::strong_ordering operator<=>(const PendingElement &other) const {
      std::uint64_t my_timestamp = get_pending_timestamp();
      std::uint64_t other_timestamp = other.get_pending_timestamp();
      if (my_timestamp < other_timestamp) {
        return std::strong_ordering::less;
      }
      if (my_timestamp > other_timestamp) {
        return std::strong_ordering::greater;
      }
      return std::strong_ordering::equal;
    }
  };

  in_place_queue<PendingElement, std::greater<PendingElement>> pending_queue;

  bool recompute_top;

  // TODO will almost certainly need to go for a new home-grown heap, one that
  // keeps the top slot temporarily empty and allows placing directly in there

  void add_from_source(std::unique_ptr<CollatorSource<T>> source) {
    std::optional<T> maybe_next = source->next_element();

    if (maybe_next.has_value()) [[likely]] {
      PendingElement pending{.data = std::move(maybe_next.value()),
                             .source = std::move(source)};

      pending_queue.push(std::move(pending));
    }
  }

public:
  std::optional<T> next_element() override {

    // We recompute the top AFTER the next iteration, because
    // we want to be able to store references into the collator
    // and return them. This removes a ton of allocations and copying

    // This is ALWAYS true outside of the first round, it would be nice to just
    // ... replace the vtable call. Could do some sort of wild
    // replace-self-at-start games?

    if (recompute_top) [[likely]] {
      assert(pending_queue.size() > 0);

      pending_queue.operate_on_top(
        [](PendingElement &pending) {
          std::optional<T> maybe_next = pending.source->next_element();
          if (maybe_next.has_value()) [[likely]] {
            pending.data = std::move(*maybe_next);
            return true;
          } else {
            return false;
          }
        }
      );
    }

    if (pending_queue.size() == 0) [[unlikely]] {
      recompute_top = false;
      return {};
    }
    recompute_top = true;
    return std::move(pending_queue.top_mut().data);
  }

  Collator(std::vector<std::unique_ptr<CollatorSource<T>>> sources) : recompute_top(false) {
    for (auto &source : sources) {
      add_from_source(std::move(source));
    }
  }
};