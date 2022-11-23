#include <span>
#include <type_traits>
#include <variant>
#include <map>

#include "optional_reference.hh"

struct Add
{
    double size;
};

struct Delete
{
    double size;
};

struct Take
{
    double size;
};

using Action = std::variant<Add, Delete, Take>;

struct BookAction
{
    double price;
    Action action;
    bool is_buy;
};

struct PureImpulseFair
{
    double buy_pressure;
    double sell_pressure;
    double depth_weight;
    int last_time;

    void update(const BookAction &event, double mid);
    void decay(int time);
};

template <typename A, typename B>
concept Comparable = requires(A a, B b) {
                         a <=> b;
                     };

template <class Update, class Mid, class Time>
    requires(
        std::is_same_v<std::span<Action>, Update> &&
        Comparable<Mid, double> &&
        std::is_same_v<Time, int>)
struct ImpulseFair
{

    PureImpulseFair impulse;

    struct Output
    {
        double pressure;
    };

    // TODO make time a special builtin
    bool call(
        optional_reference<const Update> update,
        optional_reference<const Mid> mid,
        optional_reference<const Time> time)
    {
        if (time.is_valid())
        {
            this->impulse.decay(*time);

            if (mid.is_valid() && update.is_valid())
            {
                this->impulse.update()
            }
        }
        else
        {
            return false;
        }
    }

    bool decay_timer(){};
};