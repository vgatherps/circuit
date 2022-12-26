#pragma once

#include <compare>
#include <concepts>
#include <optional>

template <class T, class C>
concept comparable_with = std::predicate<C, const T&, const T&>;

template <class T, class C = std::less<T>>
  requires comparable_with<T, C> && std::is_default_constructible_v<C>
class in_place_queue {
  std::vector<T> data;

  static std::size_t parent(std::size_t index) {
    assert(index > 0);
    return (index - 1) / 2;
  }

  static std::size_t root_child(std::size_t index) { return 1 + index * 2; }

  void bubble_down_from(std::size_t index) {
    std::size_t child_a = root_child(index);
    std::size_t child_b = 1 + child_a;

    if (child_a < data.size()) {
      C c;
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

  std::size_t just_bubble_up_from(std::size_t index) {
    if (index == 0) {
      return 0;
    }

    C c;

    std::size_t parent_index = parent(index);

    // if less(data[parent], data[index])
    // swap up and continue

    if (c(data[parent_index], data[index])) {
      std::swap(data[parent_index], data[index]);
      return just_bubble_up_from(parent_index);
    } else {
      return index;
    }
  }

  void bubble_up_from(std::size_t index) {
    std::size_t bubbled_up_index = just_bubble_up_from(index);
    bubble_down_from(bubbled_up_index);
  }

public:
  template <class F>
    requires std::predicate<F, T&>
  void operate_on_top(const F &f) {
    if (data.size() > 0) [[likely]] {
      // TODO add return type that says no modification as well?
      bool retain = f(data.front());

      if (!retain) [[likely]] {
        std::swap(data.front(), data.back());
        data.pop_back();
      }

      bubble_down_from(0);
    }
  }

  void push(T value) {
    data.emplace_back(std::move(value));
    bubble_up_from(data.size() - 1);
  }

  void pop() {
    operate_on_top([](const auto &) { return false; });
  }

  std::size_t size() const {
    return data.size();
  }

  const T& top() const {
    return data[0];
  }

  T& top_mut() {
    return data[0];
  }
};