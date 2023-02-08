from dataclasses import dataclass
from typing import Callable, List, Optional
from pycircuit.circuit_builder.circuit import HasOutput
from pycircuit.circuit_builder.circuit_context import CircuitContextManager
from pycircuit.circuit_builder.signals.regressions.linreg import LinReg
from ..running_name import get_novel_name

# TODO proper matrix abstraction


@dataclass
class Matrix:
    def __init__(self, rows: int, columns: int, fields: List[HasOutput]):
        self._rows = rows
        self._columns = columns

        if rows == 0:
            raise ValueError("Cannot create a matrixc with zero rows")
        if columns == 0:
            raise ValueError("Cannot create a matrixc with zero columns")

        if len(fields) != rows * columns:
            raise ValueError(
                f"Fields had {len(fields)} elements, "
                f"expected {rows}x{columns}={rows*columns} fields"
            )

        self._fields = fields

    @staticmethod
    def parameter_matrix(
        rows: int, columns: int, prefix: str = "matrix", required: bool = False
    ):
        circuit = CircuitContextManager.active_circuit()
        param_fields = [
            circuit.make_parameter(name=get_novel_name(prefix), required=required)
            for _i in range(rows * columns)
        ]

        return Matrix(rows, columns, param_fields)

    def index(self, row: int, column: int) -> int:
        return Matrix.get_index(self._rows, self._columns, row, column)

    def as_row_vector(self) -> List[HasOutput]:
        if self._rows != 1:
            raise ValueError(
                f"Tried to turn a matrix with {self._rows} " "rows into a row vector"
            )
        return self._fields

    def as_column_vector(self) -> List[HasOutput]:
        if self._columns != 1:
            raise ValueError(
                f"Tried to turn a matrix with {self._columns} "
                "columns into a column vector"
            )
        return self._fields

    def apply(self, fnc: Callable[[HasOutput], HasOutput]) -> "Matrix":
        return Matrix(
            rows=self.rows, columns=self.columns, fields=[fnc(f) for f in self._fields]
        )

    def add(self, other: "Matrix") -> "Matrix":
        if other.rows != self.rows or other.columns != self.columns:
            raise ValueError(
                f"Cannot add a {self.rows}x{self.columns} matrix "
                f"to a {other.rows}x{other.columns} matrix"
            )

        new_fields = [a + b for (a, b) in zip(self._fields, other._fields)]

        return Matrix(self.rows, self.columns, new_fields)

    def multiply(self, other: "Matrix") -> "Matrix":
        if self._columns != other._rows:
            raise ValueError(
                f"Cannot multiply a {self._rows}x{self._columns} matrix by a "
                f"{other._rows}x{other._columns}"
            )

        new_rows = self._rows
        new_columns = other._columns

        new_fields: List[HasOutput] = [None] * (new_columns * new_rows)  # type: ignore

        for j in range(new_columns):
            for i in range(new_rows):

                new_idx = Matrix.get_index(new_rows, new_columns, i, j)

                my_row = []
                other_column = []
                for k in range(self._columns):

                    my_idx = self.index(i, k)
                    other_idx = other.index(k, j)

                    my_row.append(self._fields[my_idx])
                    other_column.append(other._fields[other_idx])

                reg = LinReg(factors=my_row).regress(other_column)

                new_fields[new_idx] = reg

        for val in new_fields:
            assert val is not None

        return Matrix(rows=new_rows, columns=new_columns, fields=new_fields)

    def __matmul__(self, other: "Matrix") -> "Matrix":
        return self.multiply(other)

    def __add__(self, other: "Matrix") -> "Matrix":
        return self.add(other)

    @staticmethod
    def get_index(rows: int, columns: int, row: int, column: int):
        # Row major
        return (row * columns) + column

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def columns(self) -> int:
        return self._columns
