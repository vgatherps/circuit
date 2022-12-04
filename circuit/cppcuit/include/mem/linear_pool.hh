#pragma once

#include <vector>

class LinearPoolStorage {

  struct Block {
    void *data;
    std::uint64_t free;
  };

  std::vector<Block> blocks;

  void add_block(std::size_t block_size, std::size_t block_alignment);

public:
  LinearPoolStorage() = default;
  ~LinearPoolStorage() = default;
};