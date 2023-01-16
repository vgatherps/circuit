#pragma once

#include <compare>
#include <concepts>
#include <functional>
#include <type_traits>

#include <absl/container/btree_map.h>
#include <cstdint>
#include <flatbuffers/flatbuffers.h>

#include "cppcuit/side.hh"
#include "md_types/common_generated.h"
#include "signals/book_types.hh"

enum class LevelDecision { Keep, Discard };

template <class F, class Metadata>
concept LevelUpdater = requires(F f, Side s, BookLevel l, Metadata &m) {
                         { f(s, l, m) } -> std::same_as<LevelDecision>;
                       };

template <class F, class Metadata>
concept LevelCreator = requires(F f, Side s, BookLevel l) {
                         { f(s, l) } -> std::same_as<std::optional<Metadata>>;
                       };

// Bookbuilder with attached state to each level

template <class Price, class Metadata, class Comparator> class BookBuilderSide {
  absl::btree_map<Price, Metadata> levels;

public:
  template <class C, class U>
  void update_level(BookLevel level, const C &creator, const U &update) {
    auto [position, did_insert] = levels.try_emplace(level.price);

    bool keep = true;
    if (did_insert) {
      // deesign assumes this case is very rare - exchange sending out bogus
      // zero levels. Mostly trying to take advantage of hinting (should
      // benchmark) and replicating entry api, assuming most default ctors are
      // trivial
      std::optional<Metadata> maybe_level = creator(level);
      if (maybe_level.has_value()) {
        position->second = std::move(*maybe_level);
      } else {
        keep = false;
      }
    } else {
      LevelDecision keep_or_not = update(level, position->second);
      keep = keep_or_not == LevelDecision::Keep;
    }

    if (!keep) {
      levels.erase(position);
    }
  }

  template <class C, class U>
  void update_levels(const flatbuffers::Vector<const Level *> &level_updates,
                     const C &creator, const U &update) {

    for (const Level *flat_level : level_updates) {
      BookLevel level{.price = flat_level->price(), .size = flat_level->size()};
      update_level(level, creator, update);
    }
  }

  auto begin() const { return this->levels.cbegin(); }
  auto end() const { return this->levels.cend(); }
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
    const flatbuffers::Vector<const Level *> &ask_updates = *updates->asks();

    bids.update_levels(
        bid_updates, [&](BookLevel l) { return creator(Side::Buy, l); },
        [&](BookLevel l, Metadata &m) { return updater(Side::Buy, l, m); });

    asks.update_levels(
        ask_updates, [&](BookLevel l) { return creator(Side::Sell, l); },
        [&](BookLevel l, Metadata &m) { return updater(Side::Sell, l, m); });
  }

  template <LevelCreator<Metadata> C, LevelUpdater<Metadata> U>
  void update_leve(Side s, BookLevel level, const C &creator,
                   const U &updater) {

    if (s == Side::Buy) {
      bids.update_levels(
          level, [&](BookLevel l) { return creator(Side::Buy, l); },
          [&](BookLevel l, Metadata &m) { return updater(Side::Buy, l, m); });
    } else {
      asks.update_level(
          level, [&](BookLevel l) { return creator(Side::Sell, l); },
          [&](BookLevel l, Metadata &m) { return updater(Side::Sell, l, m); });
    };
  }

  auto bids_begin() const { return this->bids.begin(); }
  auto asks_begin() const { return this->asks.begin(); }
  auto bids_end() const { return this->bids.end(); }
  auto asks_end() const { return this->asks.end(); }
};