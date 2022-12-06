#include "timer/timer_queue.hh"

void RawTimerQueue::pop_head() { this->timer_events.pop(); }

void RawTimerQueue::add_event(RawTimerCall call) {
  this->timer_events.push(call);
}