#include <cstdlib>
#include <new>

#include "mem/linear_pool.hh"

void *LinearPoolStorage::add_blocks(std::size_t elem_size,
                                    std::size_t elem_alignment,
                                    std::size_t block_count) {

  if (elem_size == 0) {
    throw std::bad_alloc();
  }
  if (block_count == 0) {
    throw std::bad_alloc();
  }
  if (elem_alignment == 0) {
    throw std::bad_alloc();
  } else if (elem_alignment == 1) {
    elem_alignment = 2;
  }
  // overflow waiting to happen...
  void *data =
      std::aligned_alloc(elem_alignment, BLOCK_SIZE * elem_size * block_count);

  if (!data) {
    throw std::bad_alloc();
  }

  Block head_block = {
      .data = TPtr(data, 1),
      .free = -1,
  };

  this->blocks.reserve(this->blocks.size() + block_count);
  this->blocks.push_back(head_block);

  for (std::size_t i = 1; i < block_count; i++) {

    // compute the offset
    char *data_char = (char *)data;
    char *block_base = data_char + i * elem_size * BLOCK_SIZE;

    Block block = {
        .data = TPtr((void *)block_base, 0),
        .free = -1,
    };

    this->blocks.push_back(block);
  }

  return data;
}

void LinearPoolStorage::clear(Dtor destructor, std::size_t elem_size) {
  // iterate in reverse order, so that we can instantly free
  // a mega-block when we see the header
  for (auto block_iter = blocks.rbegin(); block_iter != blocks.rend();
       block_iter++) {

    std::uint64_t used_bits = ~block_iter->free;

    char *block_base = (char *)block_iter->data.get();

    while (used_bits != 0) {
      // TODO bit operations header utility

      std::size_t first_unused = __builtin_ffsll(used_bits);
      used_bits &= (used_bits - 1);
      std::size_t block_offset = elem_size * first_unused;

      void *object = (void *)(block_base + block_offset);

      destructor(object);
    }

    if (block_iter->data.tag()) {
      std::free(block_iter->data.get());
    }
  }

  blocks.clear();
}