#pragma once

#include "cppcuit/side.hh"
#include "math/fast_exp_64.hh"
#include "math/fast_log_64.hh"

// Impulse based book fair - the real meat involves:
// 1. Inferring book state from trades and bbos, haven't added said code yet
// 2. Inferring
class LinearBookImpulse {
  double ref_price;
  double scale;

  double bid_ask_impulses[2];

public:
  // TODO the book can/should cache the computed distances? That makes any
  // change-of-mid very expensive since you have to iterate over the whole book,
  // but especially in sim makes the cost of updating a single level higher
  void add_impulse(Side side, double price, double impulse) {
    // Why do I flip the scale instead of the distance?
    // This allows the load/subtraction subtraction
    // to happen in parallel with the subtraction
    double distance = (price - ref_price) * flip_sign_if_buy(side, scale);
    double impulse_scale = FastExpE.compute(distance);
    bid_ask_impulses[(std::uint64_t)side] += impulse * impulse_scale;
  }

  double compute_fair() const {
    double adjusted_p_ref = fast_ln(bid_ask_impulses[(int)Side::Buy] /
                                    bid_ask_impulses[(int)Side::Sell]) /
                            (2.0 * scale);
    return adjusted_p_ref + ref_price;
  }
};