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
  std::vector<AnnotatedLevel> bid_changes;
  std::vector<AnnotatedLevel> ask_changes;

  std::optional<BBO> update_levels(const DepthUpdate *updates, PlainBook &book);

public:
  struct OutputsValid {
    bool bbo;
    bool updates;
  };

  template <class I, HasBBOChanges O>
  OutputsValid on_depth(I inputs, O outputs)
    requires HAS_OPT_REF(I, DepthUpdate *, depth)
  {
    if (const DepthUpdate *depth = inputs.depth.value_or(nullptr)) {
      std::optional<BBO> bbo = update_levels(depth, outputs.book);

      OutputsValid validity{.bbo = false, .updates = false};

      if (bbo.has_value()) {
        outputs.bbo = *bbo;
        validity.bbo = true;
      }

      outputs.updates = UpdatedLevels{.bids = bid_changes, .asks = ask_changes};

      return validity;
    } else {
      return OutputsValid{.bbo = false, .updates = false};
    }
  }
};