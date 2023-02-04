#pragma once

#include <cassert>
#include <compare>
#include <concepts>
#include <functional>
#include <memory>
#include <optional>

#include "alloc/vec_list_alloc.hh"

template <class T, class C>
concept comparable_with = std::predicate<C, const T &, const T &>;

template <class T, class C = std::less<T>>
  requires comparable_with<T, C> && std::is_default_constructible_v<C>
class in_place_queue {

public:
  using RawIndex = std::uint32_t;
  using RawHandle = AllocHandle<RawIndex, T>;

private:
  VecListAlloc<T, RawIndex> alloc;
  std::vector<RawHandle> data;

  static std::size_t parent(std::size_t index) {
    assert(index > 0);
    return (index - 1) / 2;
  }

  static std::size_t root_child(std::size_t index) { return 1 + index * 2; }

  void bubble_down_from(std::size_t index) {
    std::size_t child_a = root_child(index);
    std::size_t child_b = 1 + child_a;

    if (child_a < data.size()) {
      C comp;
      auto c = [this, &comp](RawHandle a, RawHandle b) {
        return comp(this->alloc[a], this->alloc[b]);
      };
      std::optional<std::size_t> swap_index;

      // if less(data[index], data[child_a (or child_b)])
      // swap and continue from deeper index
      if (c(data[index], data[child_a])) {
        swap_index = child_a;
      } else if (child_b < data.size() && c(data[index], data[child_b])) {
        swap_index = child_b;
      }

      if (swap_index.has_value()) {
        std::swap(data[index], data[*swap_index]);
        bubble_down_from(*swap_index);
      }
    }
  }

  void bubble_up_from(std::size_t index) {
    if (index == 0) {
      return bubble_down_from(0);
    }

    C comp;
    auto c = [this, &comp](RawHandle a, RawHandle b) {
      return comp(this->alloc[a], this->alloc[b]);
    };

    std::size_t parent_index = parent(index);

    // if less(data[parent], data[index])
    // swap up and continue

    if (c(data[parent_index], data[index])) {
      std::swap(data[parent_index], data[index]);
      return bubble_up_from(parent_index);
    } else {
      return bubble_down_from(index);
    }
  }

public:
  T &operator[](RawHandle handle) { return alloc[handle]; }
  const T &operator[](RawHandle handle) const { return alloc[handle]; }

  template <class F>
    requires std::predicate<F, T &>
  void operate_on_top(const F &f) {
    if (data.size() > 0) [[likely]] {
      // TODO add return type that says no modification as well?
      bool retain = f(alloc[data.front()]);

      if (!retain) [[likely]] {
        std::swap(data.front(), data.back());
        alloc.deallocate(data.back());
        data.pop_back();
      }

      bubble_down_from(0);
    }
  }

  void push(T value) {
    RawHandle handle = alloc.allocate(std::move(value));
    data.emplace_back(handle);
    bubble_up_from(data.size() - 1);
  }

  void pop() {
    operate_on_top([](const auto &) { return false; });
  }

  std::size_t size() const { return data.size(); }

  const T &top() const { return alloc[data[0]]; }

  T &top_mut() { return alloc[data[0]]; }
};