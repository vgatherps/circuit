import torch
import torch.nn

from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin
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

from pycircuit.differentiator.tensor import CircuitParameter, make_parameter, make_constant


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
class NodeBatch:
    nodes: frozendict[str, "Node"]

    @property
    def d_nodes(self) -> Dict[str, "Node"]:
        return self.nodes


@dataclass(frozen=True, eq=True)
class OperatorNode(DataClassJsonMixin):
    output: ComponentOutput
    operator_name: str
    single_inputs: frozendict[str, "Node"]
    array_inputs: frozendict[str, FrozenList[NodeBatch]]

    @property
    def d_single_inputs(self) -> Dict[str, "Node"]:
        return self.single_inputs

    @property
    def d_array_inputs(self) -> Dict[str, FrozenList[NodeBatch]]:
        return self.array_inputs


Node = EdgeNode | OperatorNode | ParamNode | ConstantNode


# TODO the raw iteration away
# and cache already-seen nodes
def _find_edges_from(node: Node) -> Set[ComponentOutput]:
    match node:
        case EdgeNode(output=output):
            return set([output])
        case ParamNode() | ConstantNode():
            return set()
        case OperatorNode(single_inputs=single):
            array = node.d_array_inputs
            array_nodes = [
                n
                for batches in array.values()
                for batch in batches
                for n in batch.d_nodes.values()
            ]

            all_edges = set()

            for parent_node in array_nodes:
                all_edges |= _find_edges_from(parent_node)
            for parent_node in single.values():
                all_edges |= _find_edges_from(parent_node)

            return all_edges


def _load_parameter_names(node: Node) -> Set[str]:
    match node:
        case EdgeNode() | ConstantNode():
            return set()
        case ParamNode(name=name):
            return set([name])
        case OperatorNode():
            array = node.d_array_inputs
            array_nodes = [
                n
                for batches in array.values()
                for batch in batches
                for n in batch.d_nodes.values()
            ]

            all_parameters = set()

            for parent_node in array_nodes:
                all_parameters |= _load_parameter_names(parent_node)
            for parent_node in node.d_single_inputs.values():
                all_parameters |= _load_parameter_names(parent_node)

            return all_parameters


def _extract_array_batch(
    circuit: CircuitData, array: Sequence[InputBatch]
) -> FrozenList[NodeBatch]:
    batches: FrozenList[NodeBatch] = FrozenList()

    for batch in array:
        batch_dict = {
            batch_input_name: _traverse_circuit_from(circuit, batch_input)
            for (batch_input_name, batch_input) in batch.d_inputs.items()
        }
        batches.append(NodeBatch(nodes=frozendict(batch_dict)))

    batches.freeze()
    return batches


def _traverse_circuit_from(circuit: CircuitData, root: HasOutput) -> Node:
    root_output = root.output()
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
                            circuit, single
                        )
                    case ArrayComponentInput(inputs=array):
                        array_inputs[input_name] = _extract_array_batch(circuit, array)

            return OperatorNode(
                output=root_output,
                operator_name=name,
                single_inputs=frozendict(single_inputs),
                array_inputs=frozendict(array_inputs),
            )
        case name:
            raise ValueError(f"Operator name {name} not in known tensor operators")

    # Mypy can't figure this one out on it's own
    raise TypeError("unreachable")


def _traverse_pretty(node: Node) -> Any:
    match node:
        case ConstantNode(val=val):
            return str(val)
        case ParamNode(name=pname):
            return f"param({pname})"
        case EdgeNode(output=out):
            return output_to_name(out)
        case OperatorNode(
            operator_name=opname, single_inputs=single, array_inputs=array
        ):
            single_ops = {
                s_name: _traverse_pretty(s_node) for (s_name, s_node) in single.items()
            }

            array_ops = {
                a_name: [
                    {
                        b_name: _traverse_pretty(b_node)
                        for (b_name, b_node) in batch.nodes
                    }
                    for batch in a_batches
                ]
                for (a_name, a_batches) in array.items()
            }

            if array_ops:
                return {opname: [single_ops, array_ops]}
            else:
                return {opname: [single_ops]}


def _traverse_model(node: Node,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
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
            output=output,
            operator_name=opname,
        ):
            operator = ALL_OPERATORS[opname]
            singles = {
                s_name: _traverse_model(s_node, data, parameters) for (s_name, s_node) in node.d_single_inputs.items()
            }
            arrays = {
                b_name: [
                    {
                        b_id_name: _traverse_model(b_node, data, parameters)
                        for (b_id_name, b_node) in batch.d_nodes.items()
                    }
                    for batch in array
                ]
                for (b_name, array) in node.d_array_inputs.items()
            }

            return operator.operate(singles, arrays)


@dataclass
class Graph(DataClassJsonMixin):
    root: Node

    @staticmethod
    def discover_from_circuit(circuit: CircuitData, root: HasOutput) -> "Graph":
        circuit.validate()
        node = _traverse_circuit_from(circuit, root)
        return Graph(root=node)

    def find_edges(self) -> Set[ComponentOutput]:
        return _find_edges_from(self.root)

    def find_parameter_names(self) -> Set[str]:
        return _load_parameter_names(self.root)

    def pretty(self) -> Any:
        return _traverse_pretty(self.root)

    # TODO will certainly need to include more in the graph?
    # Unless tf and pytorch both do autodiscovery of inputs and variables
    def evaluate_on(
        self,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
    ) -> CircuitTensor:
        return _traverse_model(self.root, data, parameters)


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

    def edges(self) -> Set[ComponentOutput]:
        return self._graph.find_edges()
