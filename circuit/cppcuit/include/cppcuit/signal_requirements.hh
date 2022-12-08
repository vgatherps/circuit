#include <type_traits>

#include "optional_reference.hh"

#define HAS_OPT_REF(I, T, F)                                                   \
  (requires { I::F; } &&                                                       \
   std::is_same_v<optional_reference<const T>, decltype(I::F)>)

#define HAS_FIELD(O, T, F)                                                     \
  (requires { O::F; } && std::is_same_v<T, decltype(O::F)>)

#define HAS_REF_FIELD(O, T, F) HAS_FIELD(O, T &, F)