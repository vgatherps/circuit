#pragma once

#include "cppcuit/side.hh"
#include "math/fast_exp_64.hh"
#include "math/fast_log_64.hh"

#include <cmath>
#include <optional>

namespace detail {
struct TrueLinearImpulse {
  double ref_price;
  double bid_ask_impulses[2];

  void add_impulse(Side side, double price, double impulse, double scale) {
    // Why do I flip the scale instead of the distance?
    // This allows the load/subtraction subtraction
    // to happen in parallel with the subtraction
    double distance = (price - ref_price) * flip_sign_if_buy(side, scale);
    double impulse_scale = FastExpE.compute(distance);
    bid_ask_impulses[(std::uint64_t)side] += impulse * impulse_scale;
  }

  void update_reference(double reference_price, double scale) {
    double distance = (this->ref_price - reference_price) * scale;

    // Is it worth maintaining full accuracy for this expression
    double exp_distance = FastExpE.compute(distance);

    bid_ask_impulses[(int)Side::Sell] *= exp_distance;
    bid_ask_impulses[(int)Side::Buy] /= exp_distance;

    this->ref_price = reference_price;
  }

  double compute_fair(double scale) const {
    // TODO better validity checks other than just returning an infinite
    // result?
    double adjusted_p_ref = fast_ln(bid_ask_impulses[(int)Side::Buy] /
                                    bid_ask_impulses[(int)Side::Sell]) /
                            (2.0 * scale);
    return adjusted_p_ref + ref_price;
  }

  TrueLinearImpulse(double ref_price)
      : ref_price(ref_price), bid_ask_impulses{0.0, 0.0} {}
};

} // namespace detail

// Impulse based book fair - the real meat involves:
// 1. Inferring book state from trades and bbos, haven't added said code yet
// 2. Inferring book state from own fills
class LinearBookImpulse {

  double scale;

  std::optional<detail::TrueLinearImpulse> maybe_impulse;

public:
  LinearBookImpulse(double scale) : scale(scale) {}

  // TODO the book can/should cache the computed distances? That makes any
  // change-of-mid very expensive since you have to iterate over the whole book,
  // but especially in sim makes the cost of updating a single level higher

  void add_impulse(Side side, double price, double impulse) {
    if (maybe_impulse.has_value()) [[likely]] {
      maybe_impulse->add_impulse(side, price, impulse, scale);
    }
  }

  void set_reference(double reference_price) {
    if (maybe_impulse.has_value()) [[likely]] {
      maybe_impulse->update_reference(reference_price, scale);
    } else {
      maybe_impulse = detail::TrueLinearImpulse(reference_price);
    }
  }

  std::optional<double> compute_fair() const {
    if (maybe_impulse.has_value()) [[likely]] {
      return maybe_impulse->compute_fair(scale);
    } else {
      return std::nullopt;
    }
  }

  std::optional<double> reference_price() const {
    if (maybe_impulse.has_value()) [[likely]] {
      return maybe_impulse->ref_price;
    } else {
      return std::nullopt;
    }
  }

  double get_scale() const { return scale; }

  bool is_valid() const { return this->maybe_impulse.has_value(); }
};