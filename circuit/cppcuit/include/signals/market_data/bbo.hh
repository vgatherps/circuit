#pragma once

#include <concepts>

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"

using PlainBook = BookBuilder<double, double>;

template <class Op>
concept BBOCalc = (requires(const BBO &b) {
                     { Op::call(b) } -> std::same_as<double>;
                   });

template <BBOCalc Op> class BBOMath {
public:
  using Output = double;

  template <class I, class O>
    requires(HAS_OPT_REF(I, BBO, bbo) && HAS_REF_FIELD(O, double, out))
  static bool on_bbo(I inputs, O outputs) {
    if (inputs.bbo.valid()) {
      outputs.out = Op::call(*inputs.bbo);
      return true;
    } else {
      return false;
    }
  }
};

struct Mid {
  static double call(const BBO &b) { return b.mid(); }
};

struct WMid {
  static double call(const BBO &b) { return b.wmid(); }
};

template <bool Bid> struct Price {
  static double call(const BBO &b) {
    if (Bid) {
      return b.bid.price;
    } else {
      return b.ask.price;
    }
  }
};

using BBOMid = BBOMath<Mid>;
using BBOWMid = BBOMath<WMid>;
using BBOBidPrice = BBOMath<Price<true>>;
using BBOAskPrice = BBOMath<Price<false>>;