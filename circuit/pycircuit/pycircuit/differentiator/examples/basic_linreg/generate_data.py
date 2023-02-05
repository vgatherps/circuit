import numpy as np


def generate_dataset(x_coeff: float, y_coeff: float, num_elements: int):
    x_var = 0.1 * x_coeff
    y_var = 0.1 * y_coeff

    x_vals = np.arange(0, 10, num_elements) + np.random.normal(
        0.0, x_var, size=num_elements
    )
    y_vals = np.arange(0, 10, num_elements) + np.random.normal(
        0.0, y_var, size=num_elements
    )

    return x_coeff + x_vals + y_coeff + y_vals
