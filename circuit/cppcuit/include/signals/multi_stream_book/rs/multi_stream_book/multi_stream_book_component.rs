use std::collections::BTreeMap;

use circuit::component::{Component, Result, WriteData};
use circuit::core_registry::CircuitIOType;
use circuit::io_common::ComponentIOHandle;
use circuit::source_sink::{ComponentSink, ComponentSource};
use circuit::{builder::IOLoader, deref_all};
use normalized::{BookUpdate, Trade, TradeUpdate};
use time::UTCDateTime;

use super::{BookEvents, MultiStreamBook, TimedTrade};

pub struct MultiStreamBookbuilderComponent {
    book_updates: ComponentSource<BookUpdate>,
    snapshot: ComponentSource<bool>,
    trade_events: ComponentSource<TradeUpdate>,
    book: ComponentSink<MultiStreamBook<UTCDateTime>>,
    book_events: ComponentSink<BookEvents>,
}

#[inline]
pub fn trade_to_timed(trade: &Trade, trade_idx: usize) -> TimedTrade<UTCDateTime> {
    TimedTrade {
        price: trade.price,
        size: trade.size,
        side: trade.side,
        time: trade
            .exchange_timestamp
            .expect("We only support streams with complete exchange timestamps for now"),
        trade_idx,
    }
}

impl Component for MultiStreamBookbuilderComponent {
    fn call<'own: 'handle, 'handle>(
        &'own mut self,
        io: ComponentIOHandle<'handle>,
        wd: &WriteData,
    ) {
        let book = self.book.unconditional_mut_unwritten(io);
        let events = self.book_events.unconditional_mut_unwritten(io);
        events.clear();
        if let Some((update, snapshot)) = deref_all!(io, self.book_updates, self.snapshot) {
            let exchange_time = update
                .exchange_timestamp
                .expect("Multistream book only supports streams with all exchange times");
            if *snapshot {
                book.handle_snapshot(&update.bids, &update.asks, exchange_time, events)
            } else {
                book.handle_incremental_depth(&update.bids, &update.asks, exchange_time, events)
            }
        }

        if let Some(trades) = self.trade_events.as_written_ref(io) {
            let timed_trade_stream = trades
                .trades
                .iter()
                .enumerate()
                .map(|(trade_idx, trade)| trade_to_timed(trade, trade_idx));
            book.handle_trades(timed_trade_stream, events)
        }

        if !(events.bid_events.is_empty() && events.ask_events.is_empty()) {
            self.book.validate_written(wd, io);
            self.book_events.validate_written(wd, io);
        }
    }

    fn init(_: serde_json::Value, loader: &mut IOLoader) -> Result<Self> {
        Ok(Self {
            book_updates: loader.load_input("book_updates")?,
            trade_events: loader.load_input("trade_events")?,
            snapshot: loader.load_input("snapshot")?,
            book: loader.load_invalid_output("book", MultiStreamBook::default())?,
            book_events: loader.load_invalid_output("events", BookEvents::default())?,
        })
    }

    fn inputs() -> BTreeMap<String, CircuitIOType> {
        let book_ty = CircuitIOType::new::<BookUpdate>();
        let trade_ty = CircuitIOType::new::<TradeUpdate>();
        let bool_ty = CircuitIOType::new::<bool>();
        maplit::btreemap! {
            "snapshot".to_owned() => bool_ty,
            "book_updates".to_owned() => book_ty,
            "trade_events".to_owned() => trade_ty,
        }
    }

    fn outputs() -> BTreeMap<String, CircuitIOType> {
        maplit::btreemap! {
            "book".to_owned() => CircuitIOType::new::<MultiStreamBook<UTCDateTime>>(),
            "events".to_owned() => CircuitIOType::new::<BookEvents>(),
        }
    }

    fn default_output() -> Option<String> {
        Some("book".into())
    }

    fn name() -> String {
        "multi_stream_book".to_owned()
    }
}
