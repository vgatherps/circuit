#pragma once

#include <cstdint>
#include <memory>
#include <new>

template <class T, int BITS, bool MUTABLE_TAG = false> class TaggedPtr {
  std::uintptr_t raw_ptr;

  constexpr static std::uintptr_t get_mask() {

    static_assert(BITS <= 64, "Must tag pointer with multiplt bits");
    static_assert(sizeof(std::uintptr_t) == 8,
                  "Not bothering to port this to non 64-bit platforms");

    return (1 << BITS) - 1;
  }

  void _set_tag(std::uintptr_t tag) {
    const std::uintptr_t without_mask = raw_ptr & ~get_mask();
    raw_ptr = without_mask | (tag & get_mask());
  }

public:
  TaggedPtr(T *ptr, std::uintptr_t tag) {
    const std::uintptr_t without_mask = reinterpret_cast<std::uintptr_t>(ptr);

    if (without_mask & get_mask()) [[unlikely]] {
      // TODO good common out-of-line exception thrower
      throw std::runtime_error("Pointer does not respect mask limits");
    }

    raw_ptr = without_mask;
    _set_tag(tag);
  }

  TaggedPtr(T *ptr) : TaggedPtr(ptr, 0) {}

  TaggedPtr() : TaggedPtr(nullptr) {}
  TaggedPtr(const TaggedPtr &) = default;
  TaggedPtr(TaggedPtr &&) = default;
  TaggedPtr &operator=(const TaggedPtr &) = default;
  TaggedPtr &operator=(TaggedPtr &&) = default;

  T *get() const {
    const std::uintptr_t without_mask = raw_ptr & ~get_mask();
    return reinterpret_cast<T *>(without_mask);
  }

  std::uintptr_t tag() const { return raw_ptr & get_mask(); }

  void set_tag(std::uintptr_t to)
    requires MUTABLE_TAG
  {
    _set_tag(to);
  }
};