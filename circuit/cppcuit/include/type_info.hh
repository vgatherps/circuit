#pragma once

template <class T>
struct MustInvalidate
{
    constexpr bool MUST_INVALIDATE = false;
};

template <class T>
struct MustInvalidate<T *>
{
    constexpr bool MUST_INVALIDATE = true;
};

template <class T>
struct MustInvalidate<const T *>
{
    constexpr bool MUST_INVALIDATE = true;
};