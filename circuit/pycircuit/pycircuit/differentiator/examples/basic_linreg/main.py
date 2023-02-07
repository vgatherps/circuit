from pycircuit.differentiator.graph import Model, Graph
from pycircuit.differentiator.tensor import make_constant
from pycircuit.circuit_builder.component import ComponentOutput
from .generate_circuit import create_linreg_circuit
from pprint import pprint

import torch

from torch.optim import SGD

import numpy as np

REAL_X_MUL = 2
REAL_Y_MUL = -0.4


def main():
    gen = create_linreg_circuit()

    graph = Graph.discover_from_circuit(gen.circuit, gen.regress)

    pprint(graph.pretty())
    model = Model(
        graph,
    )

    print(model.edges())

    y_output = ComponentOutput(parent="external", output_name="y")
    x_output = ComponentOutput(parent="external", output_name="x")

    real_x = np.array([1, 2, 3, 4, 5])
    real_y = np.array([-4, -2, -1, 4, -5])

    real_results = REAL_X_MUL * real_x + REAL_Y_MUL * real_y

    data = {
        x_output: make_constant(real_x),
        y_output: make_constant(real_y),
    }

    optim = SGD(model.parameters_list(), lr=0.01)

    x_param = model.parameters()["x_factor"]
    y_param = model.parameters()["y_factor"]

    loss = torch.nn.MSELoss()

    module = model.create_module(data)

    print(module)

    module = torch.compile(module)

    print(module)

    def report(projected, loss):
        fxp = float(x_param)
        fyp = float(y_param)

        print("Computed loss: ", float(loss))

        print(f"Real X factor: {REAL_X_MUL}, computed X factor: {fxp}")
        print(f"Real Y factor: {REAL_Y_MUL}, computed Y factor: {fyp}")

    for _ in range(0, 100):

        projected = module()

        computed_loss = loss(projected, make_constant(real_results))

        optim.zero_grad()
        computed_loss.backward()

        report(projected, computed_loss)

        if computed_loss < 1e-4:
            break

        print()
        print()

        optim.step()

    print("Real results: ", real_results)
    print("Projected results: ", projected.detach().numpy())


if __name__ == "__main__":
    main()
