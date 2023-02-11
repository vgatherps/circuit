use super::{events::LevelEvent, BookEvent, BookEvents};
use fixed128::Fixed128;
use normalized::order_books::BookLevel;
use normalized::{Level, Side, BBO};
use std::collections::BTreeMap;
use std::{cmp::Reverse, collections::btree_map::Entry};
use time::UTCDateTime;

pub trait EventLevelAggregator<M> {
    fn new_level(&mut self, level: Level, event: LevelEvent, side: Side) -> M;
    fn update_level(
        &mut self,
        metadata: &mut M,
        current_level: Level,
        new_size: Fixed128,
        event: LevelEvent,
        side: Side,
    );
    fn remove_level(&mut self, old_level: BookLevel<M>, event: LevelEvent, side: Side);
}

impl EventLevelAggregator<()> for () {
    #[inline]
    fn new_level(&mut self, _: Level, _: LevelEvent, _: Side) {}

    #[inline]
    fn update_level(&mut self, _: &mut (), _: Level, _: Fixed128, _: LevelEvent, _: Side) {}
    #[inline]
    fn remove_level(&mut self, _: BookLevel<()>, _: LevelEvent, _: Side) {}
}

struct PartialBookLevel<M = ()> {
    size: Fixed128,
    metadata: M,
}

/// This contains a bookbuilder that operates on events
/// generated from the multi-stream book, as opposed to the bookbuilder
/// operating on plain diffs

/// This trait is called to track/update metadata on a per-level basis, using events
/// from the multi stream book
pub struct EventOrderBook<M = ()> {
    // TODO use some datastructure with a hinting api?
    bids: BTreeMap<Reverse<Fixed128>, PartialBookLevel<M>>,
    asks: BTreeMap<Fixed128, PartialBookLevel<M>>,
}

impl<M> Default for EventOrderBook<M> {
    fn default() -> Self {
        Self {
            bids: Default::default(),
            asks: Default::default(),
        }
    }
}

fn update_level<K: Ord + Eq + Copy, M, T, A: EventLevelAggregator<M>>(
    map: &mut BTreeMap<K, PartialBookLevel<M>>,
    key: K,
    event: &BookEvent<T>,
    side: Side,
    agg: &mut A,
) {
    match map.entry(key) {
        Entry::Occupied(mut e) => {
            let partial_level = e.get_mut();
            let new_size = match event.event {
                LevelEvent::Add { size } => partial_level.size + size,
                LevelEvent::Cancel { size } | LevelEvent::Take { size, .. } => {
                    partial_level.size - size
                }
                LevelEvent::Refresh { size: None } => Fixed128::zero(),
                LevelEvent::Refresh { size: Some(sz) } => sz,
            };
            assert!(
                new_size >= Fixed128::zero(),
                "We got a negative level size {} on event {:?}",
                new_size,
                event.event
            );
            if new_size > Fixed128::zero() {
                let current_level = Level::new(event.price, partial_level.size);
                partial_level.size = new_size;
                agg.update_level(
                    &mut partial_level.metadata,
                    current_level,
                    new_size,
                    event.event,
                    side,
                );
            } else {
                let partial_old_level = e.remove();
                let old_level = BookLevel {
                    price: event.price,
                    size: partial_old_level.size,
                    metadata: partial_old_level.metadata,
                };
                agg.remove_level(old_level, event.event, side);
            }
        }
        Entry::Vacant(v) => {
            let size = match event.event {
                LevelEvent::Add { size } | LevelEvent::Refresh { size: Some(size) }
                    if size > Fixed128::zero() =>
                {
                    size
                }
                _ => panic!(
                    "Tried to add new level based on event {:?} which can't add",
                    event.event
                ),
            };
            let new_level = Level::new(event.price, size);
            let metadata = agg.new_level(new_level, event.event, side);
            let partial_level = PartialBookLevel { size, metadata };
            v.insert(partial_level);
        }
    }
}

impl<M> EventOrderBook<M> {
    pub fn new() -> EventOrderBook<M> {
        EventOrderBook {
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
        }
    }

    pub fn update_book_events<T, A: EventLevelAggregator<M>>(
        &mut self,
        update: &BookEvents<T>,
        agg: &mut A,
    ) {
        for event in &update.bid_events {
            update_level(&mut self.bids, Reverse(event.price), event, Side::Buy, agg)
        }
        for event in &update.ask_events {
            update_level(&mut self.asks, event.price, event, Side::Sell, agg)
        }
    }

    pub fn bbo(&self) -> Option<BBO> {
        self.bbo_with_exchange_timestamp(None)
    }

    pub fn bbo_with_exchange_timestamp(
        &self,
        exchange_timestamp: Option<UTCDateTime>,
    ) -> Option<BBO> {
        let (plain_bid, plain_ask) = (self.bids().next(), self.asks().next());
        if let (Some(bid), Some(ask)) = (plain_bid, plain_ask) {
            Some(BBO {
                bid,
                ask,
                exchange_timestamp,
            })
        } else {
            None
        }
    }

    #[inline]
    pub fn bid_levels(&self) -> impl Iterator<Item = BookLevel<&M>> + '_ {
        self.bids
            .iter()
            .map(|(price, pbl)| BookLevel::new_with(price.0, pbl.size, &pbl.metadata))
    }

    #[inline]
    pub fn ask_levels(&self) -> impl Iterator<Item = BookLevel<&M>> + '_ {
        self.asks
            .iter()
            .map(|(price, pbl)| BookLevel::new_with(*price, pbl.size, &pbl.metadata))
    }

    #[inline]
    pub fn bid_levels_mut(&mut self) -> impl Iterator<Item = BookLevel<&mut M>> + '_ {
        self.bids
            .iter_mut()
            .map(|(price, pbl)| BookLevel::new_with(price.0, pbl.size, &mut pbl.metadata))
    }

    #[inline]
    pub fn ask_levels_mut(&mut self) -> impl Iterator<Item = BookLevel<&mut M>> + '_ {
        self.asks
            .iter_mut()
            .map(|(price, pbl)| BookLevel::new_with(*price, pbl.size, &mut pbl.metadata))
    }

    #[inline]
    pub fn bids(&self) -> impl Iterator<Item = Level> + '_ {
        self.bids
            .iter()
            .map(|(price, pbl)| Level::new(price.0, pbl.size))
    }

    #[inline]
    pub fn asks(&self) -> impl Iterator<Item = Level> + '_ {
        self.asks
            .iter()
            .map(|(price, pbl)| Level::new(*price, pbl.size))
    }

    #[inline]
    pub fn get_bid(&self, price: Fixed128) -> Option<BookLevel<&M>> {
        self.bids
            .get(&Reverse(price))
            .map(|pbl| BookLevel::new_with(price, pbl.size, &pbl.metadata))
    }

    #[inline]
    pub fn get_ask(&self, price: Fixed128) -> Option<BookLevel<&M>> {
        self.asks
            .get(&price)
            .map(|pbl| BookLevel::new_with(price, pbl.size, &pbl.metadata))
    }
}
