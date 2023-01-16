#include "signals/book_pressure/linear_impulse.hh"

LinearBookImpulse::LinearBookImpulse(double scale,
                                     const BookBuilder<double, double> &book)
    : scale(scale) {
  auto bbo = book.bbo();

  if (bbo.has_value()) {
    set_reference(bbo->mid());
  }

  for (auto [price, size] : book.bid_levels()) {
    add_impulse(Side::Buy, price, size);
  }
  for (auto [price, size] : book.ask_levels()) {
    add_impulse(Side::Sell, price, size);
  }
}