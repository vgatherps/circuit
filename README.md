
## What is a circuit

A circuit can be thought of a computation graph. A circuit consists of:

1. A set of inputs that come from outside the circuit, called external inputs
2. A set of computation nodes, each taking some set of inputs and generating some outputs.
3. A set of possible events, also called triggers. These define a set of inputs that are modified

Let's take a basic example from the codegen tests, add two numbers together. This takes two inputs, a and b, and adds them together. There's also a single event that triggers both inputs

![Directed graph describing basic dataflow to add two numbers](docs/img/add_two_numbers.svg)

We can consider another example, where we add three numbers (a, b, an c). We also do so with two distinct events, one that updates a and b, and one that updates c.

The entire circuit is

![Full circuit calltree for summing three numbers](docs/img/wide_trigger_add.svg)

and we would have two call paths generated:

![Call subtree when we update A and B](docs/img/wide_trigger_add_ab.svg)
![Call subtree when we update C](docs/img/wide_trigger_add_c.svg)

## Why Circuit?

The main selling point of circuit is to allow higher level construction of tactics without sacrificiing performance (and potentially gaining it)! How does Circuit allow this?

1. Circuit composes many small units of functionality as a dataflow graph, allowing users to declaratively specify the desired computation without having to manually manage control flow for given events
2. Circuit modules have no global state and are only concerned with their own inputs and outputs, making it safe and easy to compose anything
3. Circuit allows a full type system of inputs and outputs, so it's easy to factor out any repeated computation
4. Circuit generates C++ specialized C++ code for each given event, giving performance that rivals and can beat hand-written code
5. Circuit allows programatic construction of tactics, moving towards a code-is-data model. This allows for example generating many different signal graphs for different signals, using whatever from the library gives the best predictive power instead of a one-size-fits-all model
6. Circuit allows one to split out easily differentiable operators/parameters and train those directly, instead of relying on black-box search from simulations
7. Circuit makes it possible to transform complex black-box signals into many differentiable operators

## Differentiation

A quick and incomplete overview of circuit and differentiable operators!

Given an output and a circuit, pycircuit can trace the object graph upwards through all differentiable components. This gives you a graph that can be run with pytorch, and a list of outputs you have to record in the simulation.

The trade pressure example dumps all of this into a config, allowing you to

1. Make some circuit changes
2. Run the replayer with the generated set of outputs to record
3. Use pytorch+gradient descent to learn the parameters of the differentiable set

The commands (as run on my computer) are:

* Generate circuit, run from the upper pycircuit directory:
  * python3 -m pycircuit.trade_pressure.trade_pressure_circuit --out-dir ../cppcuit/codegen/trade_pressure
* Run a simulation, run from a build directory called build within cppcuit
  * ./bin/trade_printer/local_trade_printer --circuit_config ../config/circuit.json --stream_config ../config/streams.json --data_dir ../../data_loader/data/ --sampler_config ../../cppcuit/codegen/trade_pressure/btcusdt_binance_futures_writer_config.json --sampler_output ./dump.parquet
* Run the trainer, back from upper pycircuit:
  * python -m pycircuit.differentiator.trainer.train_graph_on --graph-file-path ../cppcuit/codegen/trade_pressure/btcusdt_binance_futures_depth_graph.json --writer-config ../cppcuit/codegen/trade_pressure/btcusdt_binance_futures_writer_config.json --parquet-path ../cppcuit/build/dump.parquet --lr=0.01

## Auxilary commands

All of these assume that you've pulled submodules and installed systemwide arrow libraries.
There's a requirements.txt in pycircuit as well

For building:

  1. Follow the pycircuit generation steps (otherwise cmake complains it can't find the circuit)
  2. python3 -m pycircuit.test_generator.generate_all_tests --out-dir ../cppcuit/generated_tests/codegen
  3. cd cppcuit
  4. mkdir build && cd build
  5. cmake -DCMAKE_BUILD_TYPE=Release ../
  6. make [add -j \<number_of_cores\> to parallelize]

For downloading data (only binance futures supported now)

1. cd dataloader
2. mkdir data
3. python -m data_loader_script.tardis_download --exchange "binance-futures" --message-type "depth" --symbol "btcusdt" --date "2022-05-01" --out-dir data/
4. Replace with your choice of date, symbol, exchange, message type ["depth", "trade"] for now. I'll add more soon as the circuit/differentiation/replay core is more complete
