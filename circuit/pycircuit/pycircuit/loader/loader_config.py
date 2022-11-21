from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


@dataclass
class CoreLoaderConfig(DataClassJsonMixin):
    root_cppcuit_path: str
    root_signals_path: str
