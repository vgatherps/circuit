#pragma once

#include <array>
#include <bitset>
#include <cstdint>
#include <new>

template <class T>
struct RawLevel
{
    double size;
    T metadata;
};

template <std::size_t N>
class RingBitSet
{
    std::bitset<N> bits;
    std::size_t offset;

    auto operator[](std::size_t at)
    {
        std::size_t true_index = (at + this->offset) % N;
        return this->bits[true_index];
    }

    auto operator[](std::size_t at) const
    {
        std::size_t true_index = (at + this->offset) % N;
        return this->bits[true_index];
    }
};

// can get one from boost right? just need to ensure power of two
// modulo works as expected

template <class T, std::size_t N>
class RingArray
{
    std::array<T, N> elems;
    std::size_t offset;

    void move_offset(std::size_t move_by)
    {
        this->offset = (this->offset + move_by) % N;
    }

    T &operator[](std::size_t at)
    {
        std::size_t true_index = (at + this->offset) % N;
        return this->elems[true_index];
    }

    const T &operator[](std::size_t at) const
    {
        std::size_t true_index = (at + this->offset) % N;
        return this->elems[true_index];
    }
};

template <class T, unsigned int N_LEVELS = 2048>
class TickBookRing
{
    static_assert(N_LEVELS & (N_LEVELS - 1) == 0);

    std::size_t offset;
    std::bitset<N> is_valid;
    std::array<T, B> elems;

    void move_offset(std::size_t move_by)
    {
        this->offset = (this->offset + move_by) % N;
    }

    // TODO move duplicate functionality into here
};