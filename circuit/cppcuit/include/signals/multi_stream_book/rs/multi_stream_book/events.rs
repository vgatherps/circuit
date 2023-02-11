use fixed128::Fixed128;

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum LevelEvent {
    Add {
        size: Fixed128,
    },
    Cancel {
        size: Fixed128,
    },
    Take {
        size: Fixed128,
        visible_size_on_book: Fixed128,
        trade_idx: usize,
    },
    Refresh {
        size: Option<Fixed128>,
    },
}
