#pragma once

template <class T>
class optional_reference
{
    T *ref;

public:
    optional_reference() : ref(nullptr) {}
    optional_reference(const optional_reference<T> &) = default;
    optional_reference(optional_reference<T> &&) = default;
    optional_reference<T> &operator=(const optional_reference<T> &) = default;
    optional_reference<T> &operator=(optional_reference<T> &&) = default;

    optional_reference(T &t) : ref(&t) {}
    optional_reference(T *t) : ref(t) {}

    T *ptr() const
    {
        return this->ref;
    }

    bool valid() const
    {
        return this->ref;
    }

    T *operator->() const
    {
        return this->ptr();
    }

    T &operator*() const
    {
        return *this->ref;
    }

    operator bool() const
    {
        return this->valid();
    }
};