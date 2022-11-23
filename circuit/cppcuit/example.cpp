#include <type_traits>
#include "optional_reference.hh"

#define HAS_OPT_REF(I, T, F) (requires { I::F; } && std::is_same_v<optional_reference<const T>, decltype(I::F)>)

template <class A, class B>
auto get_add_type(A *a, B *b)
{
    return *a + *b;
}

template <typename A, typename B>
concept Addable = requires(A a, B b) {
                      a + b;
                  };

template <class A, class B>
    requires Addable<A, B>
class Adder
{
public:
    // Probably want to do this by taking advantage of the call itself?
    struct Output
    {
        decltype(get_add_type<A, B>(nullptr, nullptr)) out;
    };

    template <class I>
        requires HAS_OPT_REF(I, A, a) && HAS_OPT_REF(I, B, b)
    static bool call(I inputs, Output &o)
    {
        if (inputs.a.valid() && inputs.b.valid())
        {
            o.out = (*inputs.a + *inputs.b);
            return true;
        }
        else
        {
            return false;
        }
    }
};

struct CircuitStruct
{
    double a;
    double b;
    Adder<double, double>::Output c;

    void call_updated_a()
    {
        struct my_input
        {
            optional_reference<const double> a;
            optional_reference<const double> b;
        };

        my_input input = {
            .a = optional_reference<const double>(this->a),
            .b = optional_reference<const double>(this->b)};

        Adder<double, double>::call(input, this->c);
    }
};

void call_c(CircuitStruct &c)
{
    c.call_updated_a();
}