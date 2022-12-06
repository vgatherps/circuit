#pragma once

#include "timer/timer_queue.hh"

class TimerHandle {
  RawTimerQueue &queue;
  void (*my_callback)(void *);

public:
  void schedule_call_at(std::uint64_t call_at_ns) {
    RawTimerCall call = {
        .callback = my_callback,
        .call_at_ns = call_at_ns,
    };

    queue.add_event(call);
  }
};