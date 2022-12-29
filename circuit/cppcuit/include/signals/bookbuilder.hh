#pragma once

#include <compare>
#include <concepts>
#include <functional>
#include <type_traits>

#include <absl/container/btree_map.h>
#include <flatbuffers/flatbuffers.h>

#include "cppcuit/side.hh"
#include "md_types/common_generated.h"

enum class LevelDecision { Keep, Discard };

template <class F, class Metadata>
concept LevelUpdater = requires(F f, Side s, Level l, Metadata &m) {
                         { f(s, l, m) } -> std::same_as<LevelDecision>;
                       };

template <class F, class Metadata>
concept LevelCreator = requires(F f, Side s, Level l) {
                         { f(s, l) } -> std::same_as<std::optional<Metadata>>;
                       };

// Bookbuilder with attached state to each level

template <class Price, class Metadata, class Comparator> class BookBuilderSide {
  absl::btree_map<Price, Metadata> levels;
  public:
  template <class C, class U>
  void update_levels(const flatbuffers::Vector<const Level *> &level_updates,
                     const C &update, const U &creator) {

    for (const Level *level : level_updates) {
      auto [position, did_insert] =
          levels.try_emplace(level->price());

      bool keep = true;
      if (did_insert) {
        // deesign assumes this case is very rare - exchange sending out bogus
        // zero levels. Mostly trying to take advantage of hinting (should
        // benchmark) and replicating entry api, assuming most default ctors are
        // trivial
        std::optional<Metadata> maybe_level = creator(*level);
        if (maybe_level.has_value()) {
          position->second = std::move(*maybe_level);
        } else {
          keep = false;
        }
      } else {
        LevelDecision keep_or_not = update(*level, position->second);
        keep = keep_or_not == LevelDecision::Keep;
      }

      if (!keep) {
        levels.erase(position);
      }
    }
  }
};

template <class Price, class Metadata>
  requires std::is_default_constructible_v<Metadata> &&
           std::is_move_assignable_v<Metadata> && requires(Price a, Price p) {
                                                    {
                                                      a > p
                                                      } -> std::same_as<bool>;
                                                  }
class BookBuilder {
  BookBuilderSide<Price, Metadata, std::less<Price>> asks;
  BookBuilderSide<Price, Metadata, std::greater<Price>> bids;

public:
  template <LevelCreator<Metadata> C, LevelUpdater<Metadata> U>
  void update_levels(const DepthUpdate *updates, const C &creator,
                     const U &updater) {
    const flatbuffers::Vector<const Level *> &bid_updates = *updates->bids();

/*


    auto sided = []<class F>(Side side, const F &f) {
      return
          [&]<class... Args>(const Args &...args) { return f(side, args...); };
    };
    bids.update_levels(bid_updates, sided(Side::Buy, updater),
                       sided(Side::Buy, creator));

*/
    const flatbuffers::Vector<const Level *> &ask_updates = *updates->asks();
    asks.update_levels(
        bid_updates,
        [&](Level l, Metadata &m) { return updater(Side::Sell, l, m); },
        [&](Level l) { return creator(Side::Sell, l); });
  }
};