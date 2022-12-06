#pragma once

class RawTimerHeap {
  struct TimeBlock {
    void *data;
    std::uint64_t fire_at_ns;
  };
};