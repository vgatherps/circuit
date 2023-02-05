#pragma once

#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/signal_requirements.hh"

#include "math/fast_exp_64.hh"
#include "math/fast_log_64.hh"

template <class A, class B, class Op>
  requires requires(A a, B b) { Op::call(a, b); }
class CoreArithmetic {
public:
  // Probably want to do this by taking advantage of the call itself?
  struct Input {
    optional_reference<const A> a;
    optional_reference<const B> b;
  };

  using Output = decltype(Op::call(*(A *)nullptr, *(B *)nullptr));

  template <class O>
    requires HAS_REF_FIELD(O, Output, out)
  static bool call(Input inputs, O &o) {
    if (inputs.a.valid() && inputs.b.valid()) {
      o.out = Op::call(*inputs.a, *inputs.b);
      return true;
    } else {
      return false;
    }
  }
};

struct DoAdd {
  template <class A, class B>
    requires requires(A a, B b) { a + b; }
  static auto call(A a, B b) {
    return a + b;
  }
};

struct DoSub {
  template <class A, class B>
    requires requires(A a, B b) { a - b; }
  static auto call(A a, B b) {
    return a - b;
  }
};

struct DoMul {
  template <class A, class B>
    requires requires(A a, B b) { a *b; }
  static auto call(A a, B b) {
    return a * b;
  }
};

struct DoDiv {
  template <class A, class B>
    requires requires(A a, B b) { a / b; }
  static auto call(A a, B b) {
    return a / b;
  }
};

struct DoMin {
  template <class A, class B>
    requires requires(A a, B b) { std::min(a, b); }
  static auto call(A a, B b) {
    return std::min(a, b);
  }
};

struct DoMax {
  template <class A, class B>
    requires requires(A a, B b) { std::max(a, b); }
  static auto call(A a, B b) {
    return std::max(a, b);
  }
};

struct DoLt {
  template <class A, class B>
    requires requires(A a, B b) { a < b; }
  static auto call(A a, B b) {
    return a < b;
  }
};

struct DoLe {
  template <class A, class B>
    requires requires(A a, B b) { a <= b; }
  static auto call(A a, B b) {
    return a <= b;
  }
};

struct DoGt {
  template <class A, class B>
    requires requires(A a, B b) { a > b; }
  static auto call(A a, B b) {
    return a > b;
  }
};

struct DoGe {
  template <class A, class B>
    requires requires(A a, B b) { a >= b; }
  static auto call(A a, B b) {
    return a >= b;
  }
};

struct DoEq {
  template <class A, class B>
    requires requires(A a, B b) { a == b; }
  static auto call(A a, B b) {
    return a == b;
  }
};

template <class A, class B> using AddComponent = CoreArithmetic<A, B, DoAdd>;
template <class A, class B> using SubComponent = CoreArithmetic<A, B, DoSub>;
template <class A, class B> using MulComponent = CoreArithmetic<A, B, DoMul>;
template <class A, class B> using DivComponent = CoreArithmetic<A, B, DoDiv>;
template <class A, class B> using MinComponent = CoreArithmetic<A, B, DoMin>;
template <class A, class B> using MaxComponent = CoreArithmetic<A, B, DoMax>;
template <class A, class B> using LtComponent = CoreArithmetic<A, B, DoLt>;
template <class A, class B> using LeComponent = CoreArithmetic<A, B, DoLe>;
template <class A, class B> using GtComponent = CoreArithmetic<A, B, DoGt>;
template <class A, class B> using GeComponent = CoreArithmetic<A, B, DoGe>;
template <class A, class B> using EqComponent = CoreArithmetic<A, B, DoEq>;

template <class A, class Op>
  requires requires(A a) { Op::call(a); }
class CoreUnary {
public:
  // Probably want to do this by taking advantage of the call itself?
  struct Input {
    optional_reference<const A> a;
  };

  using Output = decltype(Op::call(*(A *)nullptr));

  template <class O>
    requires HAS_REF_FIELD(O, Output, out)
  static bool call(Input inputs, O &o) {
    if (inputs.a.valid()) {
      o.out = Op::call(*inputs.a);
      return true;
    } else {
      return false;
    }
  }
};

struct DoAbs {
  template <class A>
    requires requires(A a) { std::abs(a); }
  static auto call(A a) {
    return std::abs(a);
  }
};

struct DoExp {
  template <class A>
    requires requires(A a) { FastExpE.compute(a); }
  static auto call(A a) {
    return FastExpE.compute(a);
  }
};

struct DoLog {
  template <class A>
    requires requires(A a) { fast_ln(a); }
  static auto call(A a) {
    return fast_ln_64(a);
  }
};

template <class A> using ExpComponent = CoreUnary<A, DoExp>;
template <class A> using AbsComponent = CoreUnary<A, DoAbs>;
template <class A> using LogComponent = CoreUnary<A, DoLog>;