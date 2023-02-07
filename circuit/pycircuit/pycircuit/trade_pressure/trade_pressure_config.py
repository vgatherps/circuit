from dataclasses import dataclass
from typing import Dict, List, Set

from dataclasses_json import DataClassJsonMixin


@dataclass
class BookFairConfig(DataClassJsonMixin):
    scale: float


@dataclass
class SingleTrade(DataClassJsonMixin):
    pricesize_weight: float
    distance_weight: float


@dataclass
class TradePressureVenueConfig(DataClassJsonMixin):
    book_fairs: List[BookFairConfig]
    trade_pressures: List[SingleTrade]


@dataclass
class TradePressureMarketConfig(DataClassJsonMixin):
    venues: Dict[str, TradePressureVenueConfig]


@dataclass
class BasicSignalConfig(DataClassJsonMixin):
    markets: Dict[str, TradePressureMarketConfig]
