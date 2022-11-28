from dataclasses import dataclass
from typing import Dict, Set

from dataclasses_json import DataClassJsonMixin


@dataclass
class TradePressureVenueConfig(DataClassJsonMixin):
    book_weight: float
    pricesize_weight: float


@dataclass
class TradePressureMarketConfig(DataClassJsonMixin):
    venues: Dict[str, TradePressureVenueConfig]


@dataclass
class TradePressureConfig(DataClassJsonMixin):
    markets: Dict[str, TradePressureMarketConfig]
