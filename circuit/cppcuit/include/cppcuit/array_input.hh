#pragma once

#include "optional_reference.hh"

// TODO this isn't actually the best representation of the struct
// for use as a parameter - the best would be to pack indices into say a uint8
// or uint16 so more fits in registers.
//
// However, this is almost entirely going to be inlined against compile-time
// constants and the index may never even be used, so there's no real point in
// hyperoptimizing the layout and potentially confusing the compiler
template <class T> class array_optional : public optional_reference<T> {

  std::size_t _index;

public:
  array_optional() = default;
  array_optional(const array_optional<T> &) = default;
  array_optional(array_optional<T> &&) = default;
  array_optional<T> &operator=(const array_optional<T> &) = default;
  array_optional<T> &operator=(array_optional<T> &&) = default;

  array_optional(T *t, std::size_t index)
      : optional_reference<T>(t), _index(index) {}
  array_optional(T *t, bool is_valid, std::size_t index)
      : array_optional(is_valid ? t : nullptr, index) {}
  array_optional(T &t, bool is_valid, std::size_t index)
      : array_optional(&t, is_valid, index) {}
  array_optional(T &t, std::size_t index) : array_optional(t, true, index) {}

  std::size_t index() const { return _index; }
};

template <class T> class array_reference {
  T &value;
  std::size_t _index;

public:
  using Type = T;
  array_reference(const array_reference<T> &other) = default;
  array_reference(array_reference<T> &&other) = default;
  array_reference<T> &operator=(const array_reference<T> &) = default;
  array_reference<T> &operator=(array_reference<T> &&) = default;

  array_reference(T &t, std::size_t index) : value(t), _index(index) {}

  T &operator*() const { return value; }
  T *operator->() const { return &value; }
  std::size_t index() const { return _index; }
};

template <class T> constexpr bool is_array_optional_v = false;
template <class T> constexpr bool is_array_optional_v<array_optional<T>> = true;

template <class T>
concept is_array_optional = is_array_optional_v<T>;

template <is_array_optional T> using ArrayOptionalType = typename T::Type;

template <class T> constexpr bool is_array_reference_v = false;
template <class T>
constexpr bool is_array_reference_v<array_reference<T>> = true;

template <class T>
concept is_array_reference = is_array_reference_v<T>;

template <is_array_reference T> using ArrayReferenceType = typename T::Type;