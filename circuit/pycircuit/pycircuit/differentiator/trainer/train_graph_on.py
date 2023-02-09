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

import sys

sys.setrecursionlimit(5000)


@dataclass
class TrainerOptions:
    graph_file_path: str
    writer_config_path: str
    parquet_path: str
    scale_by: float = 10000
    lr: float = 0.01
    lr_shrinkings: int = 1
    lr_shrink_by: float = 5
    epochs_per_run: int = 1000
    print_params: bool = False
    torch_compile: bool = False


def main():
    args = ArgumentParser(TrainerOptions).parse_args(sys.argv[1:])

    # Hacks since book fair is garbage around early day
    in_data = pd.DataFrame(
        pd.read_parquet(args.parquet_path).dropna()[1000:].reset_index(drop=True)
    )

    print(in_data)

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

    module = model.create_module(inputs)

    if args.torch_compile:
        module = torch.compile(module)

    def detect_nan(projected, loss):
        if torch.isnan(loss) or torch.any(torch.isnan(projected)):
            from pycircuit.differentiator import operator

            operator.VERBOSE = True

            projected_nan = torch.isnan(projected)

            first_true = index(projected_nan, True)

            adjusted_data = {name: data[first_true] for (name, data) in inputs.items()}

            adjusted_module = model.create_module(adjusted_data)

            adjusted_module()

            operator.VERBOSE = False

            raise ValueError("Nan encountered")

    def report(projected, loss):

        print("MSE loss: ", float(mse_loss(projected, target)))
        print(
            "Computed r^2: ", float(torchmetrics.functional.r2_score(projected, target))
        )

        if args.print_params:
            for (p_name, param) in model.parameters().items():
                print(f"{p_name}: {float(param)}, {float(param.grad)}")

    for idx in range(0, args.lr_shrinkings):
        for idx in range(0, args.epochs_per_run):

            projected = module() * args.scale_by

            computed_loss = mse_loss(projected, target)

            detect_nan(projected, computed_loss)

            optim.zero_grad()
            computed_loss.backward()

            if idx % 100 == 1 or idx == 0:
                report(projected, computed_loss)
                print()
                print()

            optim.step()

        for param_goup in optim.param_groups:
            param_goup["lr"] /= args.lr_shrink_by

    report(projected, computed_loss)


def index(tensor: torch.Tensor, value, ith_match: int = 0) -> torch.Tensor:
    """
    Returns generalized index (i.e. location/coordinate) of the first occurence of value
    in Tensor. For flat tensors (i.e. arrays/lists) it returns the indices of the occurrences
    of the value you are looking for. Otherwise, it returns the "index" as a coordinate.
    If there are multiple occurences then you need to choose which one you want with ith_index.
    e.g. ith_index=0 gives first occurence.

    Reference: https://stackoverflow.com/a/67175757/1601580
    :return:
    """
    # bool tensor of where value occurred
    places_where_value_occurs = tensor == value
    # get matches as a "coordinate list" where occurence happened
    matches = (tensor == value).nonzero()  # [number_of_matches, tensor_dimension]
    if matches.size(0) == 0:  # no matches
        return -1
    else:
        # get index/coordinate of the occurence you want (e.g. 1st occurence ith_match=0)
        index = matches[ith_match]
        return index


if __name__ == "__main__":
    main()
