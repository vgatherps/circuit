from argparse_dataclass import ArgumentParser
from dataclasses import dataclass
import json
import sys

import pandas as pd
import torch
import torchmetrics.functional
from torch.optim import SGD, Adam

from pycircuit.differentiator.trainer.data_writer_config import WriterConfig
from pycircuit.differentiator.graph import Graph, output_to_name, Model


@dataclass
class TrainerOptions:
    graph_file_path: str
    writer_config_path: str
    parquet_path: str
    scale_by: float = 10000
    lr: float = 0.01
    print_params: bool = False


def main():
    args = ArgumentParser(TrainerOptions).parse_args(sys.argv[1:])

    # Hacks since book fair is garbage around early day
    in_data = pd.DataFrame(
        pd.read_parquet(args.parquet_path).dropna()[1000:].reset_index(drop=True)
    )

    graph = Graph.from_dict(json.load(open(args.graph_file_path)))
    writer_config = WriterConfig.from_dict(json.load(open(args.writer_config_path)))

    target_returns = (in_data["target_future"] - in_data["target"]) / in_data["target"]

    if graph.find_edges() != writer_config.outputs:
        raise ValueError(
            f"""Graph and writer config recorded different edges.
Graph: {graph.find_edges()}
Writer: {writer_config.outputs}
        """
        )

    named_outputs = [output_to_name(output) for output in writer_config.outputs] + [
        "target",
        "target_future",
        "time",
    ]

    if named_outputs != list(in_data.columns):
        raise ValueError(
            f"""Input data and writer config recorded different edges.
Input data: {list(in_data.columns)}
Writer: {named_outputs}
        """
        )

    model = Model(graph)
    inputs = {
        output: torch.tensor(in_data[output_to_name(output)])
        for output in writer_config.outputs
    }

    target = torch.tensor(target_returns * args.scale_by)

    linreg_params = [
        param for name, param in model.parameters().items() if "linreg" in name
    ]
    soft_params = [
        param for name, param in model.parameters().items() if "linreg" not in name
    ]
    optim = Adam(
        [{"params": linreg_params, "lr": args.lr / 10}, {"params": soft_params}],
        lr=args.lr,
    )
    mse_loss = torch.nn.MSELoss()

    def report(projected, loss):

        print("MSE loss: ", float(mse_loss(projected, target)))
        print(
            "Computed r^2: ", float(torchmetrics.functional.r2_score(projected, target))
        )

        if args.print_params:
            for (p_name, param) in model.parameters().items():
                print(f"{p_name}: {float(param)}, {float(param.grad)}")

    for idx in range(0, 10000):

        projected = model.evaluate_on(inputs) * args.scale_by

        computed_loss = mse_loss(projected, target)

        optim.zero_grad()
        computed_loss.backward()

        if idx % 100 == 1:
            report(projected, computed_loss)
            print()
            print()

        optim.step()

    report(projected, computed_loss)


if __name__ == "__main__":
    main()
