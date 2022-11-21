import json
import sys
from dataclasses import dataclass

from argparse_dataclass import ArgumentParser

from pycircuit.pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.pycircuit.loader.loader_config import CoreLoaderConfig


@dataclass
class CallOptions:
    loader_config: str
    circuit_json: str

    call_name: str


def main():
    args = ArgumentParser(CallOptions).parse_args(sys.argv[1:])

    config = CoreLoaderConfig.from_dict(json.load(open(args.loader_config)))

    circuit = CircuitData.from_dict(json.load(open(args.circuit_json)))

    if args.name not in circuit.call_groups:
        raise ValueError(f"Call {args.name} not contained in circuit config")
