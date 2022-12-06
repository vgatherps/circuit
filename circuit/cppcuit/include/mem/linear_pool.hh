#pragma once

#include <vector>

#include "mem/tagged_ptr.hh"

// The succcess case here is generally random allocation and deallocation
// the failure case is the front N blocks are full and there's nonstop linear
// searches

class LinearPoolStorage {

  constexpr static int BLOCK_SIZE = 64;

  using TPtr = TaggedPtr<void, 1, false>;
  using Dtor = void (*)(void *);

  template <class T> friend class LinearPool;

  struct Block {
    TPtr data;
    std::uint64_t free;
  };

  std::vector<Block> blocks;

  void *add_blocks(std::size_t elem_size, std::size_t elem_alignment,
                   std::size_t block_count);
  void clear(Dtor destructor, std::size_t elem_size);

  // TODO add small free list to the front

  template <class T> __attribute__((cold)) T *add_new_blocks() {

    // inform the compiler this branch is unlikely?

    // I chose a fairly weak growth constant - thought is that growth will
    // rapidly reach steady state at start, and this avoids wasting TLB

    std::size_t blocks_to_grow = blocks.size() / 10;
    if (blocks_to_grow == 0) {
      blocks_to_grow = 1;
    }

    return (T *)add_blocks(sizeof(T), alignof(T), blocks_to_grow);
  }

  template <class T> T *get_next_ptr() {

    for (Block &block : blocks) {
      // two options:
      // 1. always search for zero first, then look for bit
      // 2. pray the compiler uses the zero flag from
      //    finding first set, and just directly calculate it
      if (block.free != 0) {
        std::size_t first_slot = __builtin_ffsll(block.free);
        std::size_t offset = first_slot * sizeof(T);
        return (T *)(offset + (char *)block.data.get());
      }
    }
    return add_new_blocks<T>();
  }
};

template <class T> class LinearPool {
  LinearPoolStorage storage;

public:
  LinearPool() = default;
  ~LinearPool() { storage.clear(); }
};