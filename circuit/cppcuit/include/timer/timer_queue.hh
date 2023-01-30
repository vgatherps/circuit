#pragma once

#include <compare>
#include <cstdint>
#include <optional>
#include <queue>
#include <vector>

struct RawTimerCall {
  std::uint64_t call_at_ns;
  void (*callback)(void *, std::uint64_t);

  std::strong_ordering operator<=>(const RawTimerCall &other) const {
    if (call_at_ns < other.call_at_ns) {
      return std::strong_ordering::less;
    }
    if (call_at_ns > other.call_at_ns) {
      return std::strong_ordering::greater;
    }
    return std::strong_ordering::equal;
  }
};

// TODO a very important optimization is to leave the head node
// uninitialized after popping. Many insertions are at or near the top
// and this provides a natural way to do less work.
// It also means that timer events are usually constant time,
// instead of requiring more work
// I'm just too lazy now to implement myself
// iirc stl heaps tend to be super slow also
class RawTimerQueue {
  std::priority_queue<RawTimerCall, std::vector<RawTimerCall>,
                      std::greater<RawTimerCall>>
      timer_events;

  bool has_first_time = false;

  // Put the nontrivial pieces of work into their own cc file
  void pop_head();
  void adjust_early_timestamps(std::uint64_t);

public:
  void add_event(RawTimerCall call);

  std::optional<std::uint64_t> next_event_time() const {
    if (timer_events.size() == 0) {
      return {};
    }
    RawTimerCall top = timer_events.top();
    return top.call_at_ns;
  }

  std::optional<RawTimerCall> get_next_event(std::uint64_t now) {
    if (!this->has_first_time) [[unlikely]] {
      this->adjust_early_timestamps(now);
      this->has_first_time = true;
    }
    if (timer_events.size() == 0) {
      return {};
    }

    RawTimerCall top = timer_events.top();
    if (top.call_at_ns > now) {
      return {};
    }

    pop_head();

    return top;
  }
};

class TimerHandle {
  RawTimerQueue &queue;
  void (*callback)(void *, std::uint64_t);

public:
  TimerHandle(RawTimerQueue &queue, void (*callback)(void *, std::uint64_t))
      : queue(queue), callback(callback) {}

  void schedule_call_at(std::uint64_t call_at_ns) {
    RawTimerCall call = {
        .call_at_ns = call_at_ns,
        .callback = callback,
    };

    queue.add_event(call);
  }
};