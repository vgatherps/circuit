#pragma once

#include <concepts>
#include <functional>

template <class... Args> class RawCall {
  const void *data;
  void (*callback)(const void *, Args...);

  template <class F>
    requires(std::invocable<F, Args...>)
  static void do_call(const void *data, Args... args) {
    const F &call = *(const F *)data;
    std::invoke(call, args...);
  }

public:
  RawCall() = default;
  RawCall(const RawCall &) = default;
  RawCall &operator=(const RawCall &) = default;

  // Pass by pointer forces the user to construct in a dedicated scope
  template <class F>
    requires(std::invocable<F, Args...>)
  RawCall(const F *call) : data(call), callback(do_call<F>) {}

  void call(Args... args) { (callback)(data, args...); }

  operator bool() const { return this->data; }
};