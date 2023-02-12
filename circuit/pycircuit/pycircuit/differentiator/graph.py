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

from pycircuit.differentiator.tensor import (
    CircuitParameter,
    make_parameter,
    make_constant,
)
from pycircuit.differentiator.operator import OperatorFn, DagOperator
from pycircuit.differentiator.tensor import Module
from pycircuit.differentiator.tensor import make_empty


def _node_from(input: Any) -> "Node":
    match input:
        case {"name": _, **kwargs} if not kwargs:
            return ParamNode.from_dict(input)
        case {"val": _, **kwargs} if not kwargs:
            return ConstantNode.from_dict(input)
        case {"output": _, **kwargs} if not kwargs:
            return EdgeNode.from_dict(input)
        case {"operator_name": _}:
            return OperatorNode.from_dict(input)

    raise ValueError(f"Cannot understand node {input}")


def output_from_name(input: str) -> ComponentOutput:
    parent, output = input.split("::")
    return ComponentOutput(parent=parent, output_name=output)


def output_to_name(output: ComponentOutput) -> str:
    return f"{output.parent}::{output.output_name}"


def encode_node_dict(input: Dict[ComponentOutput, "Node"]) -> Any:
    return {output_to_name(out): node.to_dict() for (out, node) in input.items()}


def decode_node_dict(input: Dict[str, Any]) -> Any:
    return {output_from_name(name): _node_from(node) for (name, node) in input.items()}


@dataclass
class EdgeNode(DataClassJsonMixin):
    output: ComponentOutput


# TODO stuff some more metadata into the parameter nodes
# i.e how to iterate, transformations, learning rate, etc?
@dataclass
class ParamNode(DataClassJsonMixin):
    name: str


@dataclass
class ConstantNode(DataClassJsonMixin):
    val: float


@dataclass
class NodeBatch(DataClassJsonMixin):
    nodes: Dict[str, ComponentOutput]


@dataclass
class OperatorNode(DataClassJsonMixin):
    output: ComponentOutput
    operator_name: str
    single_inputs: Dict[str, ComponentOutput]
    array_inputs: Dict[str, List[NodeBatch]]

    param_names: bool = True


Node = EdgeNode | OperatorNode | ParamNode | ConstantNode


def _extract_array_batch(
    circuit: CircuitData,
    array: Sequence[InputBatch],
    cache: Dict[ComponentOutput, Node],
    block_propagating: Set[ComponentOutput],
) -> List[NodeBatch]:
    batches = [NodeBatch(nodes=batch.d_inputs.copy()) for batch in array]

    for batch in batches:
        for output in batch.nodes.values():
            _traverse_circuit_from(circuit, output, cache, block_propagating)

    return batches


def _do_traverse_circuit_from(
    circuit: CircuitData,
    root_output: ComponentOutput,
    cache: Dict[ComponentOutput, Node],
    block_propagating: Set[ComponentOutput],
) -> Node:

    root_parent = root_output.parent

    if root_parent == "external":
        return EdgeNode(output=root_output)

    if root_output in block_propagating:
        return EdgeNode(output=root_output)

    component = circuit.components[root_parent]

    if component.options(root_output.output_name).block_propagation:
        return EdgeNode(output=root_output)

    op_name = component.definition.differentiable_operator_name
    match op_name:
        case None:
            return EdgeNode(output=root_output)
        case "constant":
            return ConstantNode(float(component.definition.metadata["constant_value"]))
        case "parameter":
            return ParamNode(name=root_parent)
        case name if name in ALL_OPERATORS:
            single_inputs: Dict[str, ComponentOutput] = {}
            array_inputs: Dict[str, List[NodeBatch]] = {}

            for (input_name, input) in component.inputs.items():
                match input:
                    case SingleComponentInput(input=single):
                        single_inputs[input_name] = single
                        _traverse_circuit_from(
                            circuit, single, cache, block_propagating
                        )
                    case ArrayComponentInput(inputs=array):
                        array_inputs[input_name] = _extract_array_batch(
                            circuit, array, cache, block_propagating
                        )

            rval = OperatorNode(
                output=root_output,
                operator_name=name,
                single_inputs=single_inputs,
                array_inputs=array_inputs,
                param_names=component.definition.metadata.get(
                    "include_param_names", True
                ),
            )
            return rval

    raise ValueError(f"Operator name {op_name} not in known tensor operators")


def _traverse_circuit_from(
    circuit: CircuitData,
    root_output: ComponentOutput,
    cache: Dict[ComponentOutput, Node],
    block_propagating: Set[ComponentOutput],
):
    if root_output in cache:
        return cache[root_output]
    rval = _do_traverse_circuit_from(circuit, root_output, cache, block_propagating)
    cache[root_output] = rval
    return rval


# TODO - should consider how to create minimal trees
# Much of the 'differentiable' computation is not attached to parameters
# and just condenses already-sampled data down.
# We should instead try and discover the minimum-sampling graph


@dataclass
class Graph(DataClassJsonMixin):

    nodes: Dict[ComponentOutput, Node] = field(
        metadata=config(encoder=encode_node_dict, decoder=decode_node_dict)
    )
    root: ComponentOutput

    @staticmethod
    def discover_from_circuit(
        circuit: CircuitData,
        root: HasOutput,
        block_propagating: Set[ComponentOutput] = set(),
    ) -> "Graph":
        circuit.validate()
        node_map: Dict[ComponentOutput, Node] = {}
        _traverse_circuit_from(circuit, root.output(), node_map, block_propagating)
        return Graph(root=root.output(), nodes=node_map)

    def find_edges(self) -> List[ComponentOutput]:

        all_edge_outputs = {
            output
            for (output, node) in self.nodes.items()
            if isinstance(node, EdgeNode)
        }
        return sorted(all_edge_outputs, key=output_to_name)

    def find_parameter_names(self) -> List[str]:
        all_parameter_names = {
            param.name for param in self.nodes.values() if isinstance(param, ParamNode)
        }
        return sorted(all_parameter_names)

    def pretty(self) -> Any:
        return self._traverse_pretty(self.root, dict())

    def traverse_model_into(
        self,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
    ) -> DagOperator:
        running_storage: List[CircuitTensor] = []
        ordered_operators: List[OperatorFn] = []
        self._traverse_model(
            self.root, data, parameters, dict(), running_storage, ordered_operators
        )

        return DagOperator(ordered=ordered_operators, storage=running_storage)

    def mark_stored(self, circuit: CircuitData):
        for edge in self.find_edges():
            circuit.components[edge.parent].force_stored(edge.output_name)

    def _do_traverse_pretty(
        self, node_output: ComponentOutput, cache: Dict[ComponentOutput, Any]
    ) -> Any:
        node = self.nodes[node_output]
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
                    s_name: self._traverse_pretty(s_node, cache)
                    for (s_name, s_node) in single.items()
                }

                array_ops = {
                    a_name: [
                        {
                            b_name: self._traverse_pretty(b_node, cache)
                            for (b_name, b_node) in batch.nodes.items()
                        }
                        for batch in a_batches
                    ]
                    for (a_name, a_batches) in array.items()
                }

                if array_ops:
                    return {opname: [single_ops, array_ops]}
                else:
                    return {opname: single_ops}

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
                    self._traverse_pretty(s_node, cache) for s_node in single.values()
                ]

                array_ops_l = [
                    [
                        [
                            self._traverse_pretty(b_node, cache)
                            for b_node in batch.nodes.values()
                        ]
                        for batch in a_batches
                    ]
                    for a_batches in array.values()
                ]

                return {opname: single_ops_l + array_ops_l}

    def _traverse_pretty(
        self, node_output: ComponentOutput, cache: Dict[ComponentOutput, Any]
    ) -> Any:
        if node_output in cache:
            return cache[node_output]

        rval = self._do_traverse_pretty(node_output, cache)
        cache[node_output] = rval
        return rval

    def _do_traverse_model(
        self,
        node_output: ComponentOutput,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
        cache: Dict[ComponentOutput, int],
        running_storage: List[CircuitTensor],
        operator_list: List[OperatorFn],
    ) -> int:
        node = self.nodes[node_output]
        match node:
            case ConstantNode(val=val):
                value = make_constant(val)
                running_storage.append(value)

            case EdgeNode(output=output):
                if output in data:
                    running_storage.append(data[output])
                else:
                    raise ValueError(f"Graph traversal could not find output {output}")

            case ParamNode(name=name):
                if name in parameters:
                    running_storage.append(parameters[name])
                else:
                    raise ValueError(f"Graph traversal could not find parameter {name}")

            case OperatorNode(
                output,
                operator_name=opname,
            ):
                operator = ALL_OPERATORS[opname]

                singles = {
                    s_name: self._traverse_model(
                        s_node, data, parameters, cache, running_storage, operator_list
                    )
                    for (s_name, s_node) in node.single_inputs.items()
                }
                arrays = {
                    b_name: [
                        {
                            b_id_name: self._traverse_model(
                                b_node,
                                data,
                                parameters,
                                cache,
                                running_storage,
                                operator_list,
                            )
                            for (b_id_name, b_node) in batch.nodes.items()
                        }
                        for batch in array
                    ]
                    for (b_name, array) in node.array_inputs.items()
                }

                write_into_idx = len(running_storage)
                oper = operator(singles, arrays, write_into_idx)
                oper.set_output(node_output)
                operator_list.append(oper)
                running_storage.append(make_empty())

            case _:
                raise TypeError("Bad node type")

        return len(running_storage) - 1

    def _traverse_model(
        self,
        node_output: ComponentOutput,
        data: Dict[ComponentOutput, CircuitTensor],
        parameters: Dict[str, CircuitParameter],
        cache: Dict[ComponentOutput, OperatorFn],
        running_storage: List[CircuitTensor],
        operator_list: List[OperatorFn],
    ) -> OperatorFn:
        if node_output in cache:
            return cache[node_output]
        rval = self._do_traverse_model(
            node_output, data, parameters, cache, running_storage, operator_list
        )
        cache[node_output] = rval
        return rval


class Model:
    def __init__(self, graph: Graph, initial_values: Dict[str, CircuitTensor] = {}):
        self._graph = graph
        parameter_names = graph.find_parameter_names()

        self._parameters = {
            name: make_parameter(initial_values.get(name)) for name in parameter_names
        }

    def create_module(self, data: Dict[ComponentOutput, CircuitTensor]):
        return self._graph.traverse_model_into(data, self._parameters)

    def parameters(self) -> Dict[str, CircuitParameter]:
        return self._parameters.copy()

    def parameters_list(self) -> List[CircuitParameter]:
        return list(self.parameters().values())

    def edges(self) -> List[ComponentOutput]:
        return self._graph.find_edges()
