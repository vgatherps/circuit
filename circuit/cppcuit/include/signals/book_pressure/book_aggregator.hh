#pragma once

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"

#include <span>

#include <nlohmann/json_fwd.hpp>

namespace detail {
class BookAggregatorBase {
protected:
  double ratio_per_group;

  using PlainBook = BookBuilder<double, double>;

  void refill_from_book(const PlainBook &book, std::size_t n,
                        std::span<double> bid_prices,
                        std::span<double> bid_sizes,
                        std::span<double> ask_prices,
                        std::span<double> ask_sizes);

  void do_init(const nlohmann::json &json);
};
} // namespace detail

template <std::size_t N>
class BookAggregator : public detail::BookAggregatorBase {

public:
  using OutputT = std::array<double, N>;

  struct OutputsValid {
    bool bid_prices, bid_sizes, ask_prices, ask_sizes;
  };

  template <class I, class O>
    requires(HAS_OPT_REF(I, PlainBook, book) &&
             HAS_REF_FIELD(O, OutputT, bid_sizes) &&
             HAS_REF_FIELD(O, OutputT, ask_sizes) &&
             HAS_REF_FIELD(O, OutputT, bid_prices) &&
             HAS_REF_FIELD(O, OutputT, ask_prices))
  OutputsValid on_book_updates(I inputs, O outputs) {
    outputs.bid_sizes[0] = 0.0;
    outputs.ask_sizes[0] = 0.0;
    if (inputs.book.valid()) {
      refill_from_book(*inputs.book, N, outputs.bid_prices, outputs.bid_sizes,
                       outputs.ask_prices, outputs.ask_sizes);
    }
    bool bids_valid = outputs.bid_sizes[0] > 0.0;
    bool asks_valid = outputs.ask_sizes[0] > 0.0;
    return OutputsValid{
        .bid_prices = bids_valid,
        .bid_sizes = bids_valid,
        .ask_prices = asks_valid,
        .ask_sizes = asks_valid,
    };
  }

  template <class O> OutputsValid init(O output, const nlohmann::json &params) {
    this->do_init(params);
    return OutputsValid{.bid_prices = false,
                        .bid_sizes = false,
                        .ask_prices = false,
                        .ask_sizes = false};
  }
};