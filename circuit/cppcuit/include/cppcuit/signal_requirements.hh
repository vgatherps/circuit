#pragma once

#include <type_traits>

#include "array_input.hh"
#include "optional_reference.hh"

#define HAS_FIELD(O, T, F)                                                     \
  (requires { O::F; } && std::is_same_v<T, decltype(O::F)>)

#define HAS_REF_FIELD(O, T, F) HAS_FIELD(O, T &, F)

#define HAS_OPT_REF(I, T, F) HAS_FIELD(I, optional_reference<const T>, F)

#define HAS_ARR_OPT(I, T, F)                                                   \
  (requires { I::F; } && is_array_optional<decltype(I::F)> &&                  \
   std::is_same_v<ArrayOptionalType<decltype(I::F)>, const T>)

#define HAS_ARR_REF(I, T, F)                                                   \
  (requires { I::F; } && is_array_reference<decltype(I::F)> &&                 \
   std::is_same_v<ArrayReferenceType<decltype(I::F)>, const T>)

template <class T, class... Ts>
bool are_same_v = std::conjunction<std::is_same<T, Ts>...>::value;

template <class T> constexpr bool valid_type = false;
template <class T> constexpr bool valid_type<const T &> = true;
template <class T> constexpr bool valid_type<array_reference<T>> = true;