#pragma once

#include <string>
#include <typeinfo>

#include "optional_reference.hh"
#include "output_handle.hh"

#include "timer/timer_queue.hh"

class Circuit {
protected:
  virtual RawOutputHandle do_real_component_lookup(const std::string &,
                                                   const std::string &,
                                                   const std::type_info &) = 0;
  virtual void *do_real_call_lookup(const std::string &,
                                    const std::type_info &) = 0;

public:
  RawTimerQueue timer;

  template <bool USE_NOW = true>
  bool examine_timer_queue(std::uint64_t current_time) {
    std::optional<RawTimerCall> maybe_call = timer.get_next_event(current_time);

    if (maybe_call.has_value()) {
      std::uint64_t time_to_use;
      if (USE_NOW || maybe_call->call_at_ns == 0) {
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
                                        const std::string &output) {
    return do_real_component_lookup(component, output, typeid(T));
  }

  template <class T> CircuitCall<T> load_callback(const std::string &name) {
    void *raw_address = do_real_call_lookup(name, typeid(T));

    return (CircuitCall<T>)raw_address;
  }
};