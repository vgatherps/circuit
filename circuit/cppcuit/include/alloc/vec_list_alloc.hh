#pragma once

#include <concepts>
#include <cstdint>
#include <limits>
#include <new>
#include <vector>

template <std::integral I, class T> class AllocHandle {
  I index;

public:
  AllocHandle() = delete;
  AllocHandle(const AllocHandle &) = default;
  AllocHandle(AllocHandle &&) = default;
  AllocHandle &operator=(const AllocHandle &) = default;
  AllocHandle &operator=(AllocHandle &&) = default;

  AllocHandle(I i) noexcept : index(i) {}
  I get() const { return index; }
};

template <std::movable T, std::integral I = std::uint32_t>
  requires(std::is_move_constructible_v<T> && std::is_move_assignable_v<T>)
class VecListAlloc {

  union ManuallyDestruct {
    std::vector<T> val;

    ManuallyDestruct() : val() {}
    ManuallyDestruct(ManuallyDestruct &&m) : val(std::move(m.val)) {}
    ~ManuallyDestruct() {}
  };

  ManuallyDestruct backing;
  std::vector<I> free_indices;
  std::vector<char> occupied;

  I add_new(T t) {
    if (backing.val.size() >= (std::size_t)std::numeric_limits<I>::max())
        [[unlikely]] {
      throw std::bad_alloc();
    }
    I idx = backing.val.size();
    backing.val.emplace_back(std::move(t));
    occupied.push_back(1);
    return idx;
  }

public:
  AllocHandle<I, T> allocate(T t) {
    if (free_indices.size() == 0) [[unlikely]] {
      return add_new(std::move(t));
    }
    I idx = free_indices.back();
    free_indices.pop_back();
    occupied[idx] = 1;

    new (&backing.val[idx]) T(std::move(t));
    return idx;
  }

  void deallocate(AllocHandle<I, T> handle) {
    // We don't need to destroy anything since trivially_destructible
    // objects can reuse the memory without calling destructor

    occupied[handle.get()] = 0;
    backing.val[handle.get()].~T();
    free_indices.push_back(handle.get());
  }

  const T &operator[](AllocHandle<I, T> handle) const {
    return backing.val[handle.get()];
  }

  T &operator[](AllocHandle<I, T> handle) { return backing.val[handle.get()]; }

  VecListAlloc() = default;
  VecListAlloc(VecListAlloc &&b)
      : backing(std::move(b.backing)), free_indices(std::move(b.free_indices)),
        occupied(std::move(b.occupied)) {}

  VecListAlloc &operator=(VecListAlloc &&b) {
    backing.val = std::move(b.backing.val);
    free_indices = std::move(b.free_indices);
    occupied = std::move(b.occupied);
    return *this;
  }

  VecListAlloc(const VecListAlloc &v) = delete;
  VecListAlloc &operator=(const VecListAlloc &) = delete;

  ~VecListAlloc() {
    for (int i = 0; i < occupied.size(); i++) {
      if (occupied[i]) {
        backing.val[i].~T();
      }
    }
  }
};