#include "signals/book_pressure/book_aggregator.hh"

#include <iostream>
#include <nlohmann/json.hpp>

namespace detail {
void BookAggregatorBase::do_init(const nlohmann::json &j) {
  j["ratio_per_group"].get_to(ratio_per_group);

  if (ratio_per_group < 0.0) {
    throw std::runtime_error("Cannot have negative bps aggregation weight");
  }
}

void BookAggregatorBase::refill_from_book(const PlainBook &book, std::size_t n,
                                          std::span<double> bid_prices,
                                          std::span<double> bid_sizes,
                                          std::span<double> ask_prices,
                                          std::span<double> ask_sizes) {

  for (std::size_t i = 0; i < n; i++) {
    bid_sizes[i] = 0.0;
    ask_sizes[i] = 0.0;
  }

  {
    auto bids = book.bids_begin();
    auto bids_end = book.bids_end();

    if (bids != bids_end) {
      bid_prices[0] = bids->first;
      bid_sizes[0] = bids->second;

      bids++;
      for (std::size_t i = 1; i < n && bids != bids_end; i++) {
        double total_size = bids->second;
        double total_pricesize = bids->first * bids->second;
        double starting_price = bids->first;
        double ending_price = starting_price * (1.0 - ratio_per_group);

        bids++;

        for (; bids != bids_end && bids->first >= ending_price; bids++) {
          total_size += bids->second;
          total_pricesize += bids->first * bids->second;
        }

        double average_price = total_pricesize / total_size;

        bid_prices[i] = average_price;
        bid_sizes[i] = total_size;
      }
    }
  }

  {
    auto asks = book.asks_begin();
    auto asks_end = book.asks_end();

    if (asks != asks_end) {
      ask_prices[0] = asks->first;
      ask_sizes[0] = asks->second;

      asks++;
      for (std::size_t i = 1; i < n && asks != asks_end; i++) {
        double total_size = asks->second;
        double total_pricesize = asks->first * asks->second;
        double starting_price = asks->first;
        double ending_price = starting_price * (1.0 + ratio_per_group);

        asks++;

        for (; asks != asks_end && asks->first <= ending_price; asks++) {
          total_size += asks->second;
          total_pricesize += asks->first * asks->second;
        }

        double average_price = total_pricesize / total_size;

        ask_prices[i] = average_price;
        ask_sizes[i] = total_size;
      }
    }
  }
}
} // namespace detail
