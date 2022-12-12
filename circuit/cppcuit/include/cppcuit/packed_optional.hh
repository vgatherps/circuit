#pragma once

#include <cmath>
#include <optional>

template <class T> struct Optionally {
  using Optional = std::optional<T>;

  static bool valid(const Optional &v) { return v.has_value(); }
  static T &value(Optional &v) { return v.value(); }
  static Optional none() { return {}; }
};

template <class T> struct Optionally<T *> {
  using Optional = T *;
  static bool valid(const Optional &o) { return o; }
  static T *value(T *v) { return v; }
  static Optional none() { return nullptr; }
};

template <> struct Optionally<double> {
  using Optional = double;

  static bool valid(const double &d) { return std::isfinite(d); }
  static double value(double d) { return d; }
  static Optional none() { return std::nan(""); }
};