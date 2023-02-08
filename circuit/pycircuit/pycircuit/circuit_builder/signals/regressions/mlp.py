from typing import Callable, List, Optional
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.signals.regressions.linreg import LinReg
from ..linalg.matrix import Matrix
from .activations import linear


class Layer:
    def __init__(
        self,
        matrix: Matrix,
        bias: Optional[Matrix] = None,
        activation: Callable[[HasOutput], HasOutput] = linear,
    ):
        self._matrix = matrix
        self._bias = bias
        self._activation = activation

        if bias is not None:
            if bias.columns != 1:
                raise ValueError(
                    f"Bias matrix of {bias.rows}x{bias.columns} must be a column vector"
                )

            if bias.rows != matrix.rows:
                raise ValueError(
                    f"Layer matrix of {matrix.rows}x{matrix.columns} "
                    f"does not match bias of {bias.rows}x1"
                )

    @staticmethod
    def parameter_layer(
        rows: int,
        columns: int,
        bias: bool = True,
        activation: Callable[[HasOutput], HasOutput] = linear,
        prefix: str = "layer",
        required: bool = False,
    ):
        matrix = Matrix.parameter_matrix(
            rows, columns, prefix=prefix, required=required
        )

        if bias:
            bias_mat = Matrix.parameter_matrix(
                matrix.rows, 1, prefix=prefix, required=required
            )
        else:
            bias_mat = None

        return Layer(matrix, bias=bias_mat, activation=activation)

    def propagate(self, col: Matrix) -> Matrix:
        col.as_column_vector()

        rval = self._matrix @ col

        if self._bias is not None:
            rval = rval + self._bias

        return rval.apply(self._activation)


def mlp(vals: List[HasOutput], layers: List[Layer]) -> List[HasOutput]:
    if len(vals) == 0:
        raise ValueError("Values list has zero length")

    if len(layers) == 0:
        raise ValueError("Layers list has zero length")

    val_mat = Matrix(rows=len(vals), columns=1, fields=vals)

    for layer in layers:
        val_mat = layer.propagate(val_mat)

    return val_mat.as_column_vector()
