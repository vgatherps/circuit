#include <type_traits>

#include "cppcuit/optional_reference.hh"
#include "cppcuit/side.hh"
#include "cppcuit/signal_requirements.hh"

template <class T> class SumOf {
public:
  using Output = T;
  using ValidTracker = bool;

  template <class A, class O>
    requires(requires(A a, double d) { d += *a.value; } &&
             HAS_REF_FIELD(O, Output, sum))

  static void call(A array_inputs, O &o) {
    o.sum += *array_inputs.value;
  }
};