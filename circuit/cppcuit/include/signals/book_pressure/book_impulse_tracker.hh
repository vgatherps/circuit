#pragma once

#include "linear_impulse.hh"

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"
#include "timer/timer_queue.hh"

#include <nlohmann/json_fwd.hpp>

class BookImpulseTracker {
  LinearBookImpulse impulse_tracker;

  using PlainBook = BookBuilder<double, double>;

  std::optional<double> handle_updates(const UpdatedLevels &updates,
                                       const PlainBook &book);

  void recompute_from_book(std::uint64_t now,
                           optional_reference<const PlainBook> book,
                           TimerHandle reschedule);

  void do_init(const nlohmann::json &json);

public:
  using FairPrice = double;

  template <class I, class O>
    requires HAS_OPT_REF(I, UpdatedLevels, updates) &&
             HAS_OPT_REF(I, PlainBook, book) &&
             HAS_REF_FIELD(O, double, fair) bool
  on_book_updates(I inputs, O outputs) {
    bool is_valid = false;

    if (inputs.updates.valid() && inputs.book.valid()) [[likely]] {
      std::optional<double> maybe_fair =
          handle_updates(*inputs.updates, *inputs.book);

      if (maybe_fair.has_value()) {
        outputs.fair = *maybe_fair;
        is_valid = true;
      }
    }

    return is_valid;
  }

  template <class I, class M>
    requires(HAS_OPT_REF(I, PlainBook, book) &&
             HAS_FIELD(M, TimerHandle, timer) &&
             HAS_FIELD(M, CircuitTime, time))
  void recompute(I input, M metadata) {
    recompute_from_book(metadata.time, input.book, metadata.timer);
  }

  template <class O, class M>
    requires(HAS_REF_FIELD(O, double, fair) &&
             HAS_FIELD(M, TimerHandle, timer)) bool
  init(O output, M metadata, const nlohmann::json &params) {
    this->do_init(params);
    metadata.timer.schedule_call_at(0);
    return false;
  }
};