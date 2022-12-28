#pragma once

#include <concepts>
#include <functional>
#include <absl/container/btree_map.h>

#include "md_types/depth_message_generated.h"

// Bookbuilder with attached state to each level

template<std::comparable Price, class Metadata>
class BookBuilder {
    absl::btree_map<Price, Metadata, std::greater<Price>> bids;
    absl::btree_map<Price, Metadata> asks;

    public:

    template<class F>
    requires std::invokable<F, Side, Level, &Metadata>
    void update_levels(const DepthMessage *depth, const F& fnc) {

    }
};