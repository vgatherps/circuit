#pragma once

#include <concepts>
#include <functional>

#include <absl/container/btree_map.h>
#include <flatbuffers/flatbuffers.h>

#include "md_types/common_generated.h"

enum class LevelDecision {
    Keep,
    Discard
};

template<class F>
concept LevelUpdater = requires(F f, Side s, Level l, Metadata& m) {
    {f(s, l, m)} -> std::same_as<LevelDecision>;
};

template<class F>
concept LevelCreator = concept LevelUpdater = requires(F f, Side s, Level l) {
    {f(s, l)} -> std::same_as<std::optional<Metadata>>;
};

// Bookbuilder with attached state to each level

template<std::comparable Price, class Metadata>
class BookBuilder {
    absl::btree_map<Price, Metadata, std::greater<Price>> bids;
    absl::btree_map<Price, Metadata> asks;

    public:

    template<LevelCreator C, LevelUpdater U>
    void update_levels(const DepthUpdate *depth, const C& update, const U& creator) {
        const auto &bids = *depth.bids();
        const auto &asks = *depth.asks();
    }
};