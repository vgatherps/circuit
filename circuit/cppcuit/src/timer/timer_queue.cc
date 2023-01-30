#include <algorithm>

#include "timer/timer_queue.hh"

void RawTimerQueue::pop_head() { this->timer_events.pop(); }

void RawTimerQueue::adjust_early_timestamps(std::uint64_t now) {
  decltype(this->timer_events) adjusted_queue;

  while (timer_events.size() > 0) {
    RawTimerCall top = this->timer_events.top();
    top.call_at_ns = std::max(top.call_at_ns, now);

    adjusted_queue.push(top);
    this->timer_events.pop();
  }

  this->timer_events = std::move(adjusted_queue);
}

void RawTimerQueue::add_event(RawTimerCall call) {
  this->timer_events.push(call);
}