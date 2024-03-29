#pragma once

#include <string>
#include <typeinfo>
#include <variant>

#include "array_input.hh"
#include "optional_reference.hh"
#include "output_handle.hh"
#include "overload.hh"

#include "timer/timer_queue.hh"

struct NoCallbackFound {};
struct WrongCallbackType {
  const std::type_info &type;
};

template <class T>
using DiscoveredCallback =
    std::variant<CircuitCall<T>, NoCallbackFound, WrongCallbackType>;

using RawDiscoveredCallback =
    std::variant<void *, NoCallbackFound, WrongCallbackType>;

class Circuit {
protected:
  virtual RawOutputHandle
  do_real_component_lookup(const std::string &, const std::string &,
                           const std::type_info &) const = 0;
  virtual RawDiscoveredCallback
  do_real_call_lookup(const std::string &, const std::type_info &) const = 0;

protected:
  CircuitTime last_called_time = 0;

  void update_time(CircuitTime new_time) {
    last_called_time =
        new_time > last_called_time ? new_time : last_called_time;
  }

public:
  RawTimerQueue timer;

  std::optional<CircuitTime> last_called_at() const {
    if (last_called_time == 0) [[unlikely]] {
      return std::nullopt;
    } else {
      return last_called_time;
    }
  }

  template <bool USE_NOW = true>
  bool examine_timer_queue(std::uint64_t current_time) {
    std::optional<RawTimerCall> maybe_call = timer.get_next_event(current_time);

    if (maybe_call.has_value()) {
      std::uint64_t time_to_use;
      if (USE_NOW) {
        time_to_use = current_time;
      } else {
        time_to_use = maybe_call->call_at_ns;
      }
      (maybe_call->callback)(this, time_to_use);
      return true;
    } else {
      return false;
    }
  }

  template <class T>
  optional_reference<const T> load_from_handle(OutputHandle<T> handle) const {
    const T *value_ptr = reinterpret_cast<const T *>(
        handle.get_offset() + reinterpret_cast<const char *>(this));
    const bool *valid_ptr = reinterpret_cast<const bool *>(
        handle.get_valid_offset() + reinterpret_cast<const char *>(this));

    return optional_reference(value_ptr, *valid_ptr);
  }

  template <class T>
  OutputHandle<T> load_component_output(const std::string &component,
                                        const std::string &output) const {
    return do_real_component_lookup(component, output, typeid(T));
  }

  template <class T>
  DiscoveredCallback<T> load_callback(const std::string &name) const {
    RawDiscoveredCallback raw_address = do_real_call_lookup(name, typeid(T));

    return std::visit(
        overloaded{
            [](void *p) -> DiscoveredCallback<T> { return (CircuitCall<T>)p; },
            [](auto x) -> DiscoveredCallback<T> { return x; }},
        raw_address);
  }
};