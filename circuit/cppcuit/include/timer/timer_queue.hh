#pragma once

#include <compare>
#include <cstdint>
#include <optional>
#include <queue>
#include <vector>

struct RawTimerCall {
  std::uint64_t call_at_ns;
  void (*callback)(void *);

  auto operator<=>(const RawTimerCall &other) const {
    return std::strong_order(call_at_ns, other.call_at_ns);
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

  // Put the nontrivial pieces of work into their own cc file
  void pop_head();

public:
  void add_event(RawTimerCall call);
  std::optional<RawTimerCall> get_next_event(std::uint64_t now) {
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
  void (*callback)(void *);

public:
  TimerHandle(RawTimerQueue &queue, void (*callback)(void *))
      : queue(queue), callback(callback) {}

  void schedule_call_at(std::uint64_t call_at_ns) {
    RawTimerCall call = {
        .call_at_ns = call_at_ns,
        .callback = callback,
    };

    queue.add_event(call);
  }
};