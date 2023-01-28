#pragma once

template <class T> class optional_reference {
  T *ref;

public:
  using Type = T;

  optional_reference() : ref(nullptr) {}
  optional_reference(const optional_reference<T> &) = default;
  optional_reference(optional_reference<T> &&) = default;
  optional_reference<T> &operator=(const optional_reference<T> &) = default;
  optional_reference<T> &operator=(optional_reference<T> &&) = default;

  optional_reference(T *t) : ref(t) {}
  optional_reference(T *t, bool is_valid)
      : optional_reference(is_valid ? t : nullptr) {}
  optional_reference(T &t, bool is_valid) : optional_reference(&t, is_valid) {}
  optional_reference(T &t) : optional_reference(t, true) {}

  const T &value_or(const T &value) {
    if (this->valid()) {
      return *ref;
    } else {
      return value;
    }
  }

  T *ptr() const { return this->ref; }

  bool valid() const { return this->ref; }

  T *operator->() const { return this->ptr(); }

  T &operator*() const { return *this->ref; }

  operator bool() const { return this->valid(); }
};