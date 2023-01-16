#pragma once

#include "cppcuit/signal_requirements.hh"
#include "signals/bookbuilder.hh"

using PlainBook = BookBuilder<double, double>;

template <class O>
concept HasChanges = HAS_REF_FIELD(O, UpdatedLevels, updates);

template <class O>
concept HasBook = HAS_REF_FIELD(O, PlainBook, book);

template <class O>
concept HasBBOChanges =
    HAS_REF_FIELD(O, BBO, bbo) && HasChanges<O> && HasBook<O>;

class BookUpdater {
  static std::optional<BBO> update_levels(const DepthUpdate *updates,
                                          PlainBook &book,
                                          UpdatedLevels &levels);

public:
  using BBO = ::BBO;
  using UpdatedLevels = ::UpdatedLevels;
  using PlainBook = ::PlainBook;

  using ConstDepthUpdate = const DepthUpdate *;
  struct OutputsValid {
    bool bbo;
    bool updates;
    bool book;
  };

  template <class I, HasBBOChanges O>
  static OutputsValid on_depth(I inputs, O outputs)
    requires HAS_OPT_REF(I, ConstDepthUpdate, depth)
  {
    if (const DepthUpdate *depth = inputs.depth.value_or(nullptr)) {
      std::optional<BBO> bbo =
          update_levels(depth, outputs.book, outputs.updates);

      OutputsValid validity{.bbo = false, .updates = true, .book = true};

      if (bbo.has_value()) {
        outputs.bbo = *bbo;
        validity.bbo = true;
      }

      return validity;
    } else {
      return OutputsValid{.bbo = false, .updates = false, .book = false};
    }
  }
};