#pragma once

#include <cmath>
#include <optional>

template <class T> struct Optionally {
  using Optional = std::optional<T>;

  bool valid(const Optional &v) const { return v.has_value() }
  static Optional none() { return {}; }
};

template <class T> struct Optionally<T *> {
  using Optional = T *;
  bool valid(const Optional &o) { return o; }
  static Optional none() { return nullptr; }
};

template <> struct Optionally<double> {
  using Optional = double;

  bool valid(const double &d) { return std::isfinite(d); }

  static Optional none() { return std::nan(nullptr); }
};