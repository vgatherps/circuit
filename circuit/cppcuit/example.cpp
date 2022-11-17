
template <class A, class B>
auto get_add_type(A *a, B *b)
{
    return *a + *b;
}

template <typename A, typename B>
concept Addable = requires(A a, B b)
{
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

    // stateless type so we don't waste space + padding on it

    static void call(const A &a, const B &b, Output &o)
    {
        o.out = a + b;
    }
};

struct CircuitStruct
{
    double a;
    double b;
    Adder<double, double>::Output c;

    void call_updated_a()
    {
        Adder<double, double>::call(this->a, this->b, this->c);
    }
};

void call_c(CircuitStruct &c)
{
    c.call_updated_a();
}