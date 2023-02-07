import torch
import torch.nn

from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin, config
from typing import Any, Dict, List, Sequence, Set
from pycircuit.circuit_builder.circuit import CircuitData
from pycircuit.circuit_builder.component import (
    HasOutput,
    ComponentOutput,
    SingleComponentInput,
    ArrayComponentInput,
)
from pycircuit.differentiator.operators.all_operators import ALL_OPERATORS
from pycircuit.circuit_builder.component import InputBatch
from pycircuit.differentiator.tensor import CircuitTensor
from frozendict import frozendict
from frozenlist import FrozenList

from pycircuit.differentiator.tensor import (
    CircuitParameter,
    make_parameter,
    make_constant,
)


def _node_from(input: Dict, cache: Dict[ComponentOutput, "Node"]) -> "Node":
    match input:
        case {"name": _, **kwargs} if not kwargs:
            return ParamNode.from_dict(input)
        case {"val": _, **kwargs} if not kwargs:
            return ConstantNode.from_dict(input)
        case {"output": _, **kwargs} if not kwargs:
            return EdgeNode.from_dict(input)
        case {"output": out, "operator_name": _}:
            output = ComponentOutput.from_dict(out)
            if output in cache:
                return cache[output]
            node = OperatorNode.cached_from_dict(input, cache)
            cache[output] = node
            return node

    raise ValueError(f"Cannot understand node {input}")


def _node_from_dict(
    input: Dict[str, Any], cache: Dict[ComponentOutput, "Node"]
) -> Dict[str, "Node"]:
    return {name: _node_from(d, cache) for (name, d) in input.items()}


def output_to_name(output: ComponentOutput) -> str:
    return f"{output.parent}::{output.output_name}"


@dataclass(eq=True, frozen=True)
class EdgeNode(DataClassJsonMixin):
    output: ComponentOutput


# TODO stuff some more metadata into the parameter nodes
# i.e how to iterate, transformations, learning rate, etc?
@dataclass(eq=True, frozen=True)
class ParamNode(DataClassJsonMixin):
    name: str


@dataclass(eq=True, frozen=True)
class ConstantNode(DataClassJsonMixin):
    val: float


@dataclass
class NodeBatch(DataClassJsonMixin):
    nodes: frozendict[str, "Node"] = field(metadata=config(decoder=_node_from_dict))

    @property
    def d_nodes(self) -> Dict[str, "Node"]:
        return self.nodes


@dataclass(frozen=True, eq=True)
class OperatorNode:
    output: ComponentOutput
    operator_name: str
    single_inputs: frozendict[str, "Node"]
    array_inputs: frozendict[str, FrozenList[NodeBatch]]

    param_names: bool = True

    @property
    def d_single_inputs(self) -> Dict[str, "Node"]:
        return self.single_inputs

    @property
    def d_array_inputs(self) -> Dict[str, FrozenList[NodeBatch]]:
        return self.array_inputs

    @staticmethod
    def cached_from_dict(input: Dict[str, Any], cache: Dict["ComponentOutput", "Node"]):
        output = ComponentOutput.from_dict(input["output"])
        operator_name = str(input["operator_name"])
        single_inputs = _node_from_dict(input["single_inputs"], cache)

        # TODO another big hack
        if "array_inputs" in input and input["array_inputs"]:
            raise ValueError(
                f"Output {output} operator {operator_name} "
                "trying to load array inputs from json before it's supported"
            )

        return OperatorNode(
            output=output,
            operator_name=operator_name,
            single_inputs=single_inputs,
            array_inputs=frozendict(),
            param_names=bool(input.get("param_names", True)),
        )


Node = EdgeNode | OperatorNode | ParamNode | ConstantNode


# TODO the raw iteration away
# and cache already-seen nodes
def _find_edges_from(node: Node, seen: Set[ComponentOutput]) -> Set[ComponentOutput]:
    match node:
        case EdgeNode(output=output):
            return set([output])
        case ParamNode() | ConstantNode():
            return set()

        case OperatorNode(output) if output in seen:
            # We've already merged in the true set from some other node
            # No need to cache intermediate seen sets everywhere
            return set()

        case OperatorNode(output, single_inputs=single):

            array = node.d_array_inputs
            array_nodes = [
                n
                for batches in array.values()
                for batch in batches
                for n in batch.d_nodes.values()
            ]

            all_edges = set()

            for parent_node in array_nodes:
                all_edges |= _find_edges_from(parent_node, seen)
            for parent_node in single.values():
                all_edges |= _find_edges_from(parent_node, seen)

            seen.add(output)

            return all_edges

    raise ValueError("Bad type")


def _load_parameter_names(node: Node, seen: Set[ComponentOutput]) -> Set[str]:
    match node:
        case EdgeNode() | ConstantNode():
            return set()
        case ParamNode(name=name):
            return set([name])
        case OperatorNode(output) if output in seen:
            return set()
        case OperatorNode(output):
            array = node.d_array_inputs
            array_nodes = [
                n
                for batches in array.values()
                for batch in batches
                for n in batch.d_nodes.values()
            ]

            all_parameters = set()

            for parent_node in array_nodes:
                all_parameters |= _load_parameter_names(parent_node, seen)
            for parent_node in node.d_single_inputs.values():
                all_parameters |= _load_parameter_names(parent_node, seen)

            seen.add(output)

            return all_parameters


def _extract_array_batch(
    circuit: CircuitData,
    array: Sequence[InputBatch],
    cache: Dict[ComponentOutput, Node],
) -> FrozenList[NodeBatch]:
    batches: FrozenList[NodeBatch] = FrozenList()

    for batch in array:
        batch_dict = {
            batch_input_name: _traverse_circuit_from(circuit, batch_input, cache)
            for (batch_input_name, batch_input) in batch.d_inputs.items()
        }
        batches.append(NodeBatch(nodes=frozendict(batch_dict)))

    batches.freeze()
    return batches


def _traverse_circuit_from(
    circuit: CircuitData, root: HasOutput, cache: Dict[ComponentOutput, Node]
) -> Node:
    root_output = root.output()

    if root_output in cache:
        return cache[root_output]

    root_parent = root_output.parent

    if root_parent == "external":
        return EdgeNode(output=root_output)

    component = circuit.components[root_parent]

    op_name = component.definition.differentiable_operator_name
    match op_name:
        case None:
            return EdgeNode(output=root_output)
        case "constant":
            return ConstantNode(float(component.definition.metadata["constant_value"]))
        case "parameter":
            return ParamNode(name=root_parent)
        case name if name in ALL_OPERATORS:
            single_inputs: Dict[str, Node] = {}
            array_inputs: Dict[str, FrozenList[NodeBatch]] = {}

            for (input_name, input) in component.inputs.items():
                match input:
                    case SingleComponentInput(input=single):
                        single_inputs[input_name] = _traverse_circuit_from(
                            circuit, single, cache
                        )
                    case ArrayComponentInput(inputs=array):
                        array_inputs[input_name] = _extract_array_batch(
                            circuit, array, cache
                        )

            rval = OperatorNode(
                output=root_output,
                operator_name=name,
                single_inputs=frozendict(single_inputs),
                array_inputs=frozendict(array_inputs),
                param_names=component.definition.metadata.get(
                    "include_param_names", True
                ),
            )
            cache[root_output] = rval
            return rval
        case name:
            raise ValueError(f"Operator name {name} not in known tensor operators")

    # Mypy can't figure this one out on it's own
    raise TypeError("unreachable")


# TODO attach metadata to more simply pretty-print
# arithmetic operators
def _traverse_pretty(node: Node, cache: Dict[ComponentOutput, Any]) -> Any:
    match node:
        case ConstantNode(val=val):
            return str(val)
        case ParamNode(name=pname):
            return f"param({pname})"
        case EdgeNode(output=out):
            return output_to_name(out)
        case OperatorNode(
            output,
            operator_name=opname,
            single_inputs=single,
            array_inputs=array,
            param_names=True,
        ):
            if output in cache:
                return cache[output]
            single_ops = {
                s_name: _traverse_pretty(s_node, cache)
                for (s_name, s_node) in single.items()
            }

            array_ops = {
                a_name: [
                    {
                        b_name: _traverse_pretty(b_node, cache)
                        for (b_name, b_node) in batch.nodes.items()
                    }
                    for batch in a_batches
                ]
                for (a_name, a_batches) in array.items()
            }

            rval: Any
            if array_ops:
                rval = {opname: [single_ops, array_ops]}
            else:
                rval = {opname: single_ops}

            cache[output] = rval

            return rval
        case OperatorNode(
            output,
            operator_name=opname,
            single_inputs=single,
            array_inputs=array,
            param_names=False,
        ):

            if output in cache:
                return cache[output]
            single_ops_l = [
                _traverse_pretty(s_node, cache) for s_node in single.values()
            ]

            array_ops_l = [
                [
                    [_traverse_pretty(b_node, cache) for b_node in batch.nodes.values()]
                    for batch in a_batches
                ]
                for a_batches in array.values()
            ]

            rval = {opname: single_ops_l + array_ops_l}

            cache[output] = rval

            return rval


def _traverse_model(
    node: Node,
    data: Dict[ComponentOutput, CircuitTensor],
    parameters: Dict[str, CircuitParameter],
    cache: Dict[ComponentOutput, CircuitTensor],
) -> CircuitTensor:
    match node:
        case ConstantNode(val=val):
            return make_constant(val)

        case EdgeNode(output=output):
            if output in data:
                return data[output]
            else:
                raise ValueError(f"Graph traversal could not find output {output}")

        case ParamNode(name=name):
            if name in parameters:
                return parameters[name]
            else:
                raise ValueError(f"Graph traversal could not find parameter {name}")

        case OperatorNode(
            output,
        ) if output in cache:
            return cache[output]

        case OperatorNode(
            output,
            operator_name=opname,
        ):
            operator = ALL_OPERATORS[opname]

            singles = {
                s_name: _traverse_model(s_node, data, parameters, cache)
                for (s_name, s_node) in node.d_single_inputs.items()
            }
            arrays = {
                b_name: [
                    {
                        b_id_name: _traverse_model(b_node, data, parameters, cache)
                        for (b_id_name, b_node) in batch.d_nodes.items()
                    }
                    for batch in array
                ]
                for (b_name, array) in node.d_array_inputs.items()
            }

            rval = operator.compute(singles, arrays)
            cache[output] = rval
            return rval


# TODO - should consider how to create minimal trees
# Much of the 'differentiable' computation is not attached to parameters
# and just condenses already-sampled data down.
# We should instead try and discover the minimum-sampling graph

# TODO give the graph a less wasteful json representation - this one
# repeatedly wastes data iterating down the graph

@dataclass
class Graph(DataClassJsonMixin):
    root: Node = field(metadata=config(decoder=_node_from))

    @staticmethod
    def discover_from_circuit(circuit: CircuitData, root: HasOutput) -> "Graph":
        circuit.validate()
        node = _traverse_circuit_from(circuit, root, dict())
        return Graph(root=node)

    def find_edges(self) -> List[ComponentOutput]:
        return sorted(_find_edges_from(self.root, set()), key=output_to_name)

    def find_parameter_names(self) -> List[str]:
        return sorted(_load_parameter_names(self.root, set()))

    def pretty(self) -> Any:
        return _traverse_pretty(self.root, dict())

    # TODO will certainly need to include more in the graph?
    # Unless tf and pytorch both do autodiscovery of inputs and variables
    def evaluate_on(
        self,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
    ) -> CircuitTensor:
        return _traverse_model(self.root, data, parameters, dict())

    def mark_stored(self, circuit: CircuitData):
        for edge in self.find_edges():
            circuit.components[edge.parent].force_stored(edge.output_name)

    @staticmethod
    def parse_from_dict(json: Dict[str, Any]) -> "Graph":
        return Graph(root=_node_from(json["root"], dict()))


class Model:
    def __init__(self, graph: Graph, initial_values: Dict[str, CircuitTensor] = {}):
        self._graph = graph
        parameter_names = graph.find_parameter_names()

        self._parameters = {
            name: make_parameter(initial_values.get(name)) for name in parameter_names
        }

    def evaluate_on(self, data: Dict[ComponentOutput, CircuitTensor]):
        return self._graph.evaluate_on(data, self._parameters)

    def parameters(self) -> Dict[str, CircuitParameter]:
        return self._parameters.copy()

    def parameters_list(self) -> List[CircuitParameter]:
        return list(self.parameters().values())

    def edges(self) -> List[ComponentOutput]:
        return self._graph.find_edges()
