#include <cmath>
#include <cassert>

#include "fast_exp_64.hh"

double fast_exp_L[256] = {};
std::uint64_t fast_exp_U[256] = {};

static int fill_exp_arrays()
{
    double lower_base = 0x10000;
    double upper_base = 0x100;
    for (int i = 0; i < 0x100; i++)
    {
        double i_d = i;
        double lower_power = i_d / lower_base;
        fast_exp_L[i] = std::pow(2.0, lower_power);

        double upper_power = i_d / upper_base;

        double two_upper = std::pow(2.0, upper_power);

        assert(two_upper >= 1.0);
        assert(two_upper <= 2.0);

        fast_exp_U[i] = *reinterpret_cast<std::uint64_t *>(&two_upper);
    }
}

int __force_early_fill = fill_exp_arrays();