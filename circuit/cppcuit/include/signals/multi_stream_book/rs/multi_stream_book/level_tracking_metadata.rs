use std::{cmp::Ordering, fmt::Debug};

use fixed128::Fixed128;
use time::UTCDateTime;

use super::events::LevelEvent;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TimestampedOffset<T> {
    pub time: T,
    pub trade_sz: Fixed128,
    pub implied_add: Fixed128,
}

impl<T> TimestampedOffset<T> {
    #[inline]
    pub fn new(time: T, trade_sz: Fixed128, implied_add: Fixed128) -> Self {
        Self {
            time,
            trade_sz,
            implied_add,
        }
    }
}

#[derive(Default, Debug, PartialEq, Eq)]
pub struct LevelTracker<T = UTCDateTime> {
    pub expected_trades: Vec<TimestampedOffset<T>>,
    pub diff_size: Fixed128,
    pub last_ts: T,
    pub marked_for_deletion_at: Option<T>,
}

impl<T> LevelTracker<T>
where
    T: Ord + PartialOrd + Copy + Debug,
{
    pub fn default_with_ts(timestamp: T) -> Self {
        Self {
            expected_trades: Vec::new(),
            diff_size: Fixed128::zero(),
            last_ts: timestamp,
            marked_for_deletion_at: None,
        }
    }

    pub fn mark_for_deletion(&mut self, delete_time: T, events: &mut Vec<LevelEvent>) {
        self.validate();

        if delete_time <= self.last_size_time() {
            return;
        }

        let current_inferred_size = self.inferred_size();

        self.marked_for_deletion_at = Some(delete_time);

        let size_to_cancel_first = current_inferred_size;

        let total_size_remove = self.total_size_removal();

        // If we have a level that is now too small for the trades that we have buffered,
        // we have to regenerate synthetic adds and cancels again
        // TODO TODO TODO I think this logic is wrong and will not work
        // we right now just ignore total traded volume when we have a mark?
        // I think we need to examine trades *after* the mark
        let surplus_traded = total_size_remove - self.diff_size;
        debug_assert!(total_size_remove >= surplus_traded);

        self.account_for_surplus_trades_at(surplus_traded, size_to_cancel_first, events);

        let new_inferred_size = self.inferred_size();

        let diff = new_inferred_size - current_inferred_size;
        match diff.cmp(&Fixed128::zero()) {
            Ordering::Greater => events.push(LevelEvent::Add { size: diff }),
            Ordering::Less => events.push(LevelEvent::Cancel { size: -diff }),
            Ordering::Equal => (),
        }

        self.validate();
    }

    pub fn new_diff_size(
        &mut self,
        new_size: Fixed128,
        diff_time: T,
        events: &mut Vec<LevelEvent>,
    ) {
        self.validate();

        debug_assert!(new_size >= Fixed128::zero());
        let current_inferred_size = self.inferred_size();

        match self.marked_for_deletion_at {
            Some(m) if m <= diff_time => self.marked_for_deletion_at = None,
            _ => (),
        }

        // in here, if we have still marked the level for deletion,
        // we have to count up the trades we've removed
        // and generate additions for those

        // Consider the true series of events:
        // 1. X dollars at price Y are added
        // 2. somebody takes X/2 at price Y
        //
        // However we see the trade ahead of time
        //
        // We should be able to infer from this that somebody added at least X/2 liquidity at price Y
        // despite not having seen the diff yet
        let surplus_size_from_trades = if self.marked_for_deletion_at.is_none() {
            self.expected_trades.retain(|t| t.time > diff_time);
            Fixed128::zero()
        } else {
            self.expected_trades
                .drain_filter(|t| t.time <= diff_time)
                .map(|t| t.trade_sz - t.implied_add)
                .sum::<Fixed128>()
        };

        // Discount any size increases from ones we expected
        // If we've added inferred liqudiity as above, and the see the size start to increase,
        // we discount that size increase from the inferred liquidity
        let mut surplus_new_size = surplus_size_from_trades + new_size - self.diff_size;

        for trade in &mut self.expected_trades {
            if surplus_new_size <= Fixed128::zero() {
                break;
            }

            // we have to gate here on trades *before* removing any known size
            // since we know this addition cannot interact with them
            match self.marked_for_deletion_at {
                Some(m) if m < trade.time => continue,
                _ => (),
            }
            let new_surplus = surplus_new_size - trade.implied_add;
            trade.implied_add = (trade.implied_add - surplus_new_size).max(Fixed128::zero());
            surplus_new_size = new_surplus;
        }

        // We'll never publish an increased size from the inferred size check when we are
        // marked to be deleted. However, knowing that we have more surplus, we have
        // to add and re-cancel said liquidity

        // Consider the following events:
        // 1. X/2 dollars are added at price Y
        // 2. X/2 more dollars are added at price Y
        // 3. level Y is cancelled
        // 4. a trade happens deeper in the book
        //
        // 1. X/2 dollars are added at price Y
        // We see the first increase, and then see the deep trade (implying this level is cancelled)
        // When we see the second increase, we need to both add and cancel it
        if surplus_new_size > Fixed128::zero() && self.marked_for_deletion_at.is_some() {
            events.push(LevelEvent::Add {
                size: surplus_new_size,
            });
            events.push(LevelEvent::Cancel {
                size: surplus_new_size,
            });
        }

        let size_to_cancel_first =
            (self.diff_size - new_size).clamp(Fixed128::zero(), current_inferred_size);

        self.diff_size = new_size;

        let total_size_remove = self.total_size_removal();

        // If we have a level that is now too small for the trades that we have buffered,
        // we have to regenerate synthetic adds and cancels again
        let surplus_traded = total_size_remove - self.diff_size;

        if surplus_traded > Fixed128::zero() {
            // Can we ever entry this case on a size increase?
            // I don't think so and plan to assert so
            assert!(surplus_new_size <= Fixed128::zero())
        }

        debug_assert!(total_size_remove >= surplus_traded);

        self.account_for_surplus_trades_at(surplus_traded, size_to_cancel_first, events);

        let new_inferred_size = self.inferred_size();

        let diff = new_inferred_size - current_inferred_size;
        match diff.cmp(&Fixed128::zero()) {
            Ordering::Greater => events.push(LevelEvent::Add { size: diff }),
            Ordering::Less => events.push(LevelEvent::Cancel { size: -diff }),
            Ordering::Equal => (),
        }

        self.last_ts = diff_time.max(self.last_ts);

        self.validate();
    }

    pub fn on_trade(
        &mut self,
        trade_size: Fixed128,
        trade_idx: usize,
        trade_time: T,
        events: &mut Vec<LevelEvent>,
    ) -> bool {
        self.validate();
        if trade_time <= self.last_ts {
            return false;
        }

        let current_inferred_size = self.inferred_size();

        let trade = LevelEvent::Take {
            size: trade_size,
            visible_size_on_book: current_inferred_size,
            trade_idx,
        };

        if trade_size > current_inferred_size {
            let add_size = trade_size - current_inferred_size;
            let offset = TimestampedOffset::new(trade_time, trade_size, add_size);
            self.append_new_trade(offset);

            events.push(LevelEvent::Add { size: add_size });
            events.push(trade);

            if self.marked_for_deletion_at.is_none() {
                debug_assert_eq!(self.total_size_removal(), self.diff_size); // Implies that the inferred size is zero
            } else {
                debug_assert_eq!(self.total_size_removal(), Fixed128::zero());
            }
            debug_assert_eq!(self.inferred_size(), Fixed128::zero()); // Implies that the inferred size is zero
        } else {
            let offset = TimestampedOffset::new(trade_time, trade_size, Fixed128::zero());
            self.append_new_trade(offset);

            events.push(trade);

            let new_inferred_size = self.inferred_size();
            debug_assert_eq!(new_inferred_size, current_inferred_size - trade_size);
        }

        self.validate();
        true
    }

    pub fn append_new_trade(&mut self, trade: TimestampedOffset<T>) {
        match self.expected_trades.last_mut() {
            Some(t) if t.time == trade.time => {
                t.implied_add += trade.implied_add;
                t.trade_sz += trade.trade_sz;
            }
            _ => self.expected_trades.push(trade),
        }
    }

    // These will all persist in fuzz tests and testing, but turn into empty statements
    // on a release build
    pub fn validate(&self) {
        for trade in &self.expected_trades {
            debug_assert!(trade.trade_sz >= trade.implied_add);
            debug_assert!(trade.trade_sz >= Fixed128::zero());
            debug_assert!(trade.implied_add >= Fixed128::zero());
        }
        debug_assert!(self.total_size_removal() >= Fixed128::zero());
        debug_assert!(self.total_size_removal() <= self.diff_size);
        debug_assert!(self.inferred_size() >= Fixed128::zero());
        debug_assert!(self.inferred_size() <= self.diff_size);

        // If we are marked for deletion, this only includes trades that come
        // after the deletion event. This should hence be net neutral
        if self.marked_for_deletion_at.is_some() {
            debug_assert_eq!(self.total_size_removal(), Fixed128::zero())
        }
    }

    pub fn last_size_time(&self) -> T {
        // We write this to None if it's stale, so it only
        // exists conditional on being newer
        self.marked_for_deletion_at.unwrap_or(self.last_ts)
    }

    pub fn total_size_removal(&self) -> Fixed128 {
        self.expected_trades
            .iter()
            .filter(|t| {
                self.marked_for_deletion_at
                    .map(|m| m < t.time)
                    .unwrap_or(true)
            })
            .map(|t| t.trade_sz - t.implied_add)
            .sum::<Fixed128>()
    }

    pub fn inferred_size(&self) -> Fixed128 {
        if self.marked_for_deletion_at.is_some() {
            return Fixed128::zero();
        }
        let rval = self.diff_size - self.total_size_removal();
        debug_assert!(rval >= Fixed128::zero());
        rval
    }
}

impl<T> LevelTracker<T> {
    pub fn definitely_gone(&self) -> bool {
        self.diff_size == Fixed128::zero() && self.expected_trades.is_empty()
    }

    pub fn account_for_surplus_trades_at(
        &mut self,
        mut surplus_traded: Fixed128,
        size_to_cancel_first: Fixed128,
        events: &mut Vec<LevelEvent>,
    ) {
        if surplus_traded > Fixed128::zero() {
            // First, cancel off the volume BEFORE the add, since we know it's early
            // and part of the diff
            let should_cancel_later = if size_to_cancel_first > Fixed128::zero() {
                let remains = (surplus_traded - size_to_cancel_first).max(Fixed128::zero());
                let can_cancel = surplus_traded.min(size_to_cancel_first);

                assert!(can_cancel > Fixed128::zero());

                events.push(LevelEvent::Cancel { size: can_cancel });

                remains
            } else {
                surplus_traded
            };
            events.push(LevelEvent::Add {
                size: surplus_traded,
            });

            // We then re-cancel volume that we've seen afterwards since it has to come after the adds
            if should_cancel_later > Fixed128::zero() {
                events.push(LevelEvent::Cancel {
                    size: should_cancel_later,
                });
            }

            for trade in &mut self.expected_trades {
                if surplus_traded <= Fixed128::zero() {
                    break;
                }
                let possible_add = trade.trade_sz - trade.implied_add;
                debug_assert!(possible_add >= Fixed128::zero());
                let new_surplus = surplus_traded - possible_add;
                trade.implied_add += possible_add.min(surplus_traded);
                surplus_traded = new_surplus
            }

            // PROVE we can never have a surplus in excess of traded volume
            // This is because the surplus is bounded from above by the total size to remove
            // and the total size to remove is equal to the total take volume on the books
            debug_assert!(surplus_traded <= Fixed128::zero());
        }
    }
}

#[cfg(test)]
mod tests {
    use fixed128::{fixed, Fixed128};

    use crate::multi_stream_book::events::LevelEvent;

    use super::LevelTracker;

    // True series of events:
    // 1. Level is added at size X, price Y
    // 1. Level is resized to X/2

    // Events we see are:
    // 1. We see the add for X at Y
    //  * We generate an add for X
    // 2. We see the resize to X/2
    //  * We generate a cancel for X/2
    #[test]
    fn test_cancel() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let add_time = 3;

        tracker.new_diff_size(level_size, add_time, &mut events);
        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);

        assert_eq!(tracker.total_size_removal(), Fixed128::zero());
        assert_eq!(tracker.inferred_size(), level_size);

        events.clear();
        tracker.new_diff_size(level_size / 2u64, add_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Cancel {
                size: level_size / 2u64
            }]
        );

        assert_eq!(tracker.inferred_size(), level_size / 2u64);
    }

    // True series of events:
    // 1. Level is added at size X, price Y
    // 2. Someone trades through the entire level

    // Events we see are:
    // 1. We see the add for X at Y
    //  * We generate an add for X
    // 2. A trade happens at price Y for size X
    //  * We generate a take of X at Y
    // 3. We see the diff for 0, and this exises the buffered trade
    //  * We see the level is gone, and has no buffered trades left
    #[test]
    fn test_trade_before_remove() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let trade_size = fixed!(2);
        let add_time = 3;
        let trade_time = 5;

        tracker.new_diff_size(trade_size, add_time, &mut events);
        assert_eq!(events, vec![LevelEvent::Add { size: trade_size }]);

        assert_eq!(tracker.total_size_removal(), Fixed128::zero());
        assert_eq!(tracker.inferred_size(), trade_size);

        events.clear();
        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Take {
                size: trade_size,
                visible_size_on_book: trade_size,
                trade_idx: 0,
            }]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), trade_size);

        events.clear();

        tracker.new_diff_size(Fixed128::zero(), trade_time, &mut events);
        assert_eq!(events, vec![]);
        assert_eq!(tracker, LevelTracker::default_with_ts(trade_time));
    }

    // True series of events:
    // 1. Level is added, size X price Y
    // 2. Take clears level

    // Events we see are:
    // 1. A trade happens at price Y for size X
    //  * We generate a synthetic add for X and a trade for X,
    // 2. We see the add for X at Y
    //  * We remove our synthetic add but otherwise don't act, since we already saw the add
    // 3. We see the diff for 0, and this exises the buffered trade
    //  * We see the level is gone, and has no buffered trades left
    #[test]
    fn test_early_trade() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let trade_size = fixed!(2);
        let add_time = 3;
        let trade_time = 5;

        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(trade_size, add_time, &mut events);
        assert_eq!(events, vec![]);

        assert_eq!(tracker.total_size_removal(), trade_size);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        tracker.new_diff_size(Fixed128::zero(), trade_time, &mut events);
        assert_eq!(events, vec![]);
        assert_eq!(tracker, LevelTracker::default_with_ts(trade_time));
    }

    // almost same as above but we split into two trades
    // to check merging logic
    #[test]
    fn test_early_trade_merge() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let trade_size = fixed!(2);
        let add_time = 3;
        let trade_time = 5;

        tracker.on_trade(trade_size / 2u64, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: trade_size / 2u64
                },
                LevelEvent::Take {
                    size: trade_size / 2u64,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.on_trade(trade_size / 2u64, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: trade_size / 2u64
                },
                LevelEvent::Take {
                    size: trade_size / 2u64,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(trade_size, add_time, &mut events);
        assert_eq!(events, vec![]);

        assert_eq!(tracker.total_size_removal(), trade_size);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        tracker.new_diff_size(Fixed128::zero(), trade_time, &mut events);
        assert_eq!(events, vec![]);
        assert_eq!(tracker, LevelTracker::default_with_ts(trade_time));
    }

    // True series of events:
    // 1. Level is added, size X price Y
    // 2. Level is canceled
    // 3. Level is added, size X price Y
    // 4. Take clears level

    // Events we see are:
    // 1. A trade happens at price Y for size X
    //  * We generate a synthetic add for X and a trade for X,
    // 2. We see the add for X at Y
    //  * We remove our synthetic add but otherwise don't act, since we already saw the add
    // 3. We see the diff for 0, however this *does not* excise the added trade
    //  * We must generate a synthetic add and a cancel, since we realize liquidity must have been added and deleted
    //  * The cancel comes second so we don't generate a bad intermediate state
    // 4. We see the add for X at Y.
    //  * This clears our next synthetic add from the buffer, but otherwise has no impact
    // 5. We see the final diff for zero, which excises the trades
    //  * This should result in a cleared state
    #[test]
    fn test_early_trade_reinsert() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let trade_size = fixed!(2);
        let add_time = 1;
        let remove_time = 2;
        let re_add_time = 3;
        let trade_time = 4;

        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(trade_size, add_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.total_size_removal(), trade_size);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        tracker.new_diff_size(Fixed128::zero(), remove_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Cancel { size: trade_size },
            ]
        );

        assert_eq!(tracker.total_size_removal(), Fixed128::zero());
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();

        tracker.new_diff_size(trade_size, re_add_time, &mut events);
        assert_eq!(events, vec![]);

        assert_eq!(tracker.total_size_removal(), trade_size);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        tracker.new_diff_size(Fixed128::zero(), trade_time, &mut events);
        assert_eq!(events, vec![]);
        assert_eq!(tracker, LevelTracker::default_with_ts(trade_time));
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. A trade takes out X/2
    // 3. The level is resized to X

    // Delivered series of events
    // 1. We see the trade for X/2
    //  * Add X/2
    //  * Take X/2
    // 2. We see the diff for X, with the later timestamp of 3
    // * Remove the synthetic add for X/2 and cached trade
    // * Generate an add for X

    #[test]
    fn test_interleaved_add_trade() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let trade_size = fixed!(1);
        let level_size = trade_size * fixed!(2);
        let first_trade_time = 1;
        let re_add_time = 3;

        tracker.on_trade(trade_size, 0, first_trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, re_add_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());
        assert_eq!(tracker.inferred_size(), level_size);
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. A trade takes out X/2
    // 3. The level is resized to X/4

    // Delivered series of events
    // 1. We see the trade for X/2
    //  * Add X/2
    //  * Take X/2
    // 2. We see the diff for X/4, with the later timestamp of 3
    // * Remove the synthetic add for X/2 and cached trade
    // * Generate an add for X/4

    // Notably, the true order stream is add X, trade x/2, cancel x/4.
    // This is invisible to us since we never see information that there were more adds
    // However the result sums up properly

    #[test]
    fn test_interleaved_add_trade_cancel() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let true_level_size = fixed!(2);
        let trade_size = true_level_size / 2u64;
        let level_size = true_level_size / 4u64;
        let first_trade_time = 1;
        let re_add_time = 3;

        tracker.on_trade(trade_size, 0, first_trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, re_add_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Add {
                size: true_level_size / 4u64
            }]
        );
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());
        assert_eq!(tracker.inferred_size(), level_size);
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. The size is decreased to X/2
    // 3. The size is increased to 2X
    // 4. A trade takes out 3x/2

    // Delivered series of events
    // 1. We see the diff for X
    //  * We generate an add for X
    // 2. We see the trade for 3x/2
    //  * We generate a synthetic add of X/2
    //  * We generate a take of 3x/2
    // 3. We see the diff for X/2 (before the trade)
    //  * We have to generate another add of X/2
    //  * We generate a cancel of X/2
    //  * The add comes before the cancel, otherwise we have a negative intermediate state
    #[test]
    fn test_interleaved_add_large_trade_early_cancel() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let trade_size = fixed!(3) * level_size / fixed!(2);
        let small_level_size = level_size / 2u64;
        let first_diff_time = 0;
        let second_diff_time = 1;
        let trade_time = 3;

        tracker.new_diff_size(level_size, first_diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);

        assert_eq!(tracker.inferred_size(), level_size);
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();

        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: trade_size - level_size
                },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: level_size,
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), level_size);

        events.clear();
        tracker.new_diff_size(small_level_size, second_diff_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: level_size - small_level_size
                },
                LevelEvent::Cancel {
                    size: level_size - small_level_size
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), small_level_size);
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. The size is decreased to X/4
    // 3. The size is increased to X
    // 4. A trade takes out X/2

    // Delivered series of events
    // 1. We see the diff for X
    //  * We generate an add for X
    // 2. We see the trade for X/2
    //  * We generate a take of X/2
    // 3. We see the diff for X/4 (before the trade)
    //  * We generate a cancel of X/4. This can come first since it doesn't send us negative
    //  * We have to generate another add of X/4
    //  * We also generate the remaining cancel of X/2
    #[test]
    fn test_interleaved_add_small_trade_early_cancel() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let trade_size = level_size / fixed!(2);
        let small_level_size = level_size / 4u64;
        let first_diff_time = 0;
        let second_diff_time = 1;
        let trade_time = 3;

        tracker.new_diff_size(level_size, first_diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);

        assert_eq!(tracker.inferred_size(), level_size);
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();

        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Take {
                size: trade_size,
                visible_size_on_book: level_size,
                trade_idx: 0,
            }]
        );

        assert_eq!(tracker.inferred_size(), level_size - trade_size);
        assert_eq!(tracker.total_size_removal(), trade_size);

        events.clear();
        tracker.new_diff_size(small_level_size, second_diff_time, &mut events);

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), small_level_size);

        assert_eq!(
            events,
            vec![
                LevelEvent::Cancel {
                    size: small_level_size
                },
                LevelEvent::Add {
                    size: small_level_size
                },
                LevelEvent::Cancel {
                    size: level_size / 2u64
                },
            ]
        );
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. The size is decreased to 0
    // 2. A level is added for X at price Y again
    // 4. A trade takes out X/2

    // Delivered series of events
    // 1. We see the trade for X/2
    //  * We generate a synthetic add of X/2
    //  * We generate a take of X/2
    // 2. We see the diff for X (before the trade)
    //  * We generate an add of X / 2, remove the synthetic add
    // 2. We see the diff for 0 (before the trade)
    //  * We generate a cancel of X/2 (only partially, since we don't have surplus)
    //  * We generate another synthetic add of X/2
    //  * We commplete the cancellation by adding the final cancel for X/2
    #[test]
    fn test_multiple_reconcilliation_cancels() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let trade_size = level_size / fixed!(2);
        let second_diff_time = 1;
        let trade_time = 3;

        tracker.on_trade(trade_size, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: trade_size },
                LevelEvent::Take {
                    size: trade_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, second_diff_time, &mut events);
        assert_eq!(
            events,
            vec![LevelEvent::Add {
                size: level_size - trade_size
            }]
        );

        assert_eq!(tracker.inferred_size(), level_size - trade_size);
        assert_eq!(tracker.total_size_removal(), trade_size);

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), second_diff_time, &mut events);

        assert_eq!(tracker.inferred_size(), Fixed128::zero());
        assert_eq!(tracker.total_size_removal(), Fixed128::zero());

        assert_eq!(
            events,
            vec![
                LevelEvent::Cancel { size: trade_size },
                LevelEvent::Add { size: trade_size },
                LevelEvent::Cancel {
                    size: level_size - trade_size
                },
            ]
        );
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. We mark the level for future deletion
    // 3. We see a diff for 0

    // Delivered series of events
    // 1. We see the diff for X
    //  * Add X
    // 2. We mark X for deletion
    // * Generate a cancel for X
    // 3. We mark X for deletion
    // * No events

    #[test]
    fn test_basic_deletion_mark() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let mark_time = 3;

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);
        assert_eq!(tracker.inferred_size(), level_size);

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Cancel { size: level_size }]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. We see a trade for X/2
    // 3. We mark the level for future deletion
    // 4. We see a diff for 0

    // Delivered series of events
    // 1. We see the diff for X
    //  * Add X
    // 2. We see a trade for X/2
    // * Generate a take for X/2
    // 3. We mark X for deletion
    // * Generate a cancel for remaining X / 2
    // 4. See a diff for zero
    // * No events

    #[test]
    fn test_mixed_trade_mark() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let trade_time = 2;
        let mark_time = 3;

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);
        assert_eq!(tracker.inferred_size(), level_size);

        events.clear();
        tracker.on_trade(level_size / 2u64, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Take {
                size: level_size / 2u64,
                visible_size_on_book: level_size,
                trade_idx: 0,
            }]
        );
        assert_eq!(tracker.inferred_size(), level_size / 2u64);

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(
            events,
            vec![LevelEvent::Cancel {
                size: level_size / 2u64
            }]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. We see a trade for X/2
    // 3. We mark the level for future deletion
    // 4. We see a diff for 0

    // Delivered series of events
    // 1. We see a trade for X/2
    // * Generate an add for X/2
    // * Generate an take for X/2
    // 3. We mark X for deletion
    // * No new events generated
    // 4. See a diff for zero
    // * No events

    #[test]
    fn test_mark_early_trade() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let trade_time = 2;
        let mark_time = 3;

        tracker.on_trade(level_size / 2u64, 0, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: level_size / 2u64
                },
                LevelEvent::Take {
                    size: level_size / 2u64,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. X is canceled
    // 3. We mark the level for future deletion (implies the prior cancel)
    // 4. Somebody adds X/2
    // 3. We see a trade for X/2
    // 4. We see a diff for 0

    // Delivered series of events
    // 1. We see the diff for X
    //  * Add X
    // 3. We mark X for deletion
    // * Generate a cancel for X
    // 2. We see a trade for X/2
    // * Generate a take for X/2
    // 4. See a diff for zero
    // * No events

    #[test]
    fn test_trade_after_mark() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let mark_time = 2;
        let trade_time = 3;

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);
        assert_eq!(tracker.inferred_size(), level_size);

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Cancel { size: level_size }]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.on_trade(level_size / 2u64, 3, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add {
                    size: level_size / 2u64
                },
                LevelEvent::Take {
                    size: level_size / 2u64,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 3,
                },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. Size is increased to 2X
    // 3. 2X is canceled
    // 4. We mark the level for future deletion (implies the prior cancel)
    // 7. We see a diff for 0

    // Delivered series of events
    // 1. We see the diff for X
    //  * Add X
    // 2. We mark X for deletion
    // * Generate a cancel for X
    // 3. We see an add for 2x
    // * Generate another add for X
    // * Generate another cancel for X
    // 4. See a diff for zero
    // * No events

    #[test]
    fn test_add_after_mark() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let mark_time = 2;

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Add { size: level_size }]);
        assert_eq!(tracker.inferred_size(), level_size);

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![LevelEvent::Cancel { size: level_size }]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size + level_size, diff_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: level_size },
                LevelEvent::Cancel { size: level_size },
            ]
        );

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. X is canceled
    // 3. We mark the level for future deletion (implies the prior cancel)
    // 4. A level is added for X at price Y again
    // 5. A trade clears X

    // Delivered series of events
    // 1. We see the take of X
    //  * Add X
    //  * Take X
    // 2. Level is marked for deletion (with a timestamp earlier than the trade)
    //  * No events
    // 3. We see an add for X
    //   * Add size X
    //   * Remove size X
    //   * We regenerate events since we know that somebody had to add/delete in order to make it work
    // 3. We see a diff of 0
    //   * No events

    // Equivalently to the above, a level can be marked before existing
    // If we see a buy at 11, that implicitly marks 10 for deletion
    // So when we see a take at 10 later, we have an implicit early 'mark for deletion'

    #[test]
    fn test_mark_trade_reordering() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let mark_time = 2;
        let delete_time = 4;

        events.clear();
        tracker.on_trade(level_size, 0, delete_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: level_size },
                LevelEvent::Take {
                    size: level_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 0,
                },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: level_size },
                LevelEvent::Cancel { size: level_size },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), delete_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }

    // True series of events:
    // 1. A level is added for X at price Y
    // 2. X is traded through
    // 3. A level is added for X at price Y again
    // 4. X is canceled
    // 5. We mark the level for future deletion (implies the prior cancel)

    // Delivered series of events
    // 1. We see the take of X
    //  * Add X
    //  * Take X
    // 2. Level is marked for deletion (with a timestamp later than the trade)
    //  * No events
    // 3. We see an add for X with a timestamp before the trade
    //   * No events
    // 4. We see an add for X with a timestamp after the trade and before the mark
    //   * We generate an add for X
    //   * We generate a cancel for X
    // 5. We see a diff of 0
    //   * No events

    // Equivalently to the above, a level can be marked before existing
    // If we see a buy at 11, that implicitly marks 10 for deletion
    // So when we see a take at 10 later, we have an implicit early 'mark for deletion'

    #[test]
    fn test_mark_trade_reordering_2() {
        let mut tracker = LevelTracker::default();
        let mut events = Vec::new();

        let level_size = fixed!(2);
        let diff_time = 1;
        let trade_time = 2;
        let second_diff_time = 3;
        let mark_time = 4;

        events.clear();
        tracker.on_trade(level_size, 1, trade_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: level_size },
                LevelEvent::Take {
                    size: level_size,
                    visible_size_on_book: fixed!(0),
                    trade_idx: 1,
                },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.mark_for_deletion(mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, diff_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(level_size, second_diff_time, &mut events);

        assert_eq!(
            events,
            vec![
                LevelEvent::Add { size: level_size },
                LevelEvent::Cancel { size: level_size },
            ]
        );
        assert_eq!(tracker.inferred_size(), Fixed128::zero());

        events.clear();
        tracker.new_diff_size(Fixed128::zero(), mark_time, &mut events);

        assert_eq!(events, vec![]);
        assert_eq!(tracker.inferred_size(), Fixed128::zero());
    }
}
