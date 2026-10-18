from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from lines import lines
from numpy.polynomial.chebyshev import chebfit, chebval

from despero.echelle import COLUMN_CENTER, SPEED_OF_LIGHT, fit_echelle_solution
from despero.fit import fit_line_with_gaussian, gaussian
from despero.parameters import ECHELLE_FIT_DEGREE_COLUMN
from despero.store.order_coordinates import OrderCoordinates
from despero.utils import load_comp_standard

LIVE_PLOT = False
GAUSS_FIT_WINDOW = 20
RESIDUAL_LIMIT = 0.01  # in A, only for coloring the residuals in the plots
# orders taken from a different ThAr exposure than the rest (commit ba612ef): each gets a free zero point in the 2D fit
SPLICED_ORDERS = [0, 1, 60, 61, 62, 63]

removed_lines = {}

def plot_order(comp_standard: Any, order_number: int, gauss_params: list[dict], order_lines: list) -> None:
    order = comp_standard.orders[order_number]
    _, ax = plt.subplots(nrows=2, sharex=True)
    ax[0].set_title(f"Order #{order_number}")
    ax[0].plot(order.coordinates.columns, order.intensity, color="black", lw=2)
    ax[0].set_ylabel("Normalized intensity")
    ax[1].set_ylabel(r"Wavelength (${\AA}$)")
    ax[1].set_xlabel("Column number")
    if order_lines is not None and len(order_lines):
        inc_y_shift = np.max(order.intensity) / (len(order_lines) + 1)
        wavelength = chebval(order.coordinates.columns, order.coordinates.coeff)
        ax[1].plot(order.coordinates.columns, wavelength, color="green", lw=2)
        coeffs = [f"{coef:.3f}" for coef in order.coordinates.coeff]
        ax[1].text(0.2, 0.8, ("Coeffs: " + ", ".join(coeffs)), transform=ax[1].transAxes, ha="center", va="center")
        for i, line in enumerate(order_lines):
            params = gauss_params[i]
            if len(params):  # gaussian fit exists for line
                col = params["x0"]
                # only draw the gaussian around the line peak
                x_fit = np.linspace(params["x0"] - GAUSS_FIT_WINDOW, params["x0"] + GAUSS_FIT_WINDOW, 100)
                gauss = gaussian(x_fit, params["a"], params["x0"], params["sigma"], params["offset"])
                ax[0].plot(x_fit, gauss, color="green", alpha=0.5, lw=3)
            else:  # no fit for the line
                col = line[0]
            wl_fit = chebval([col], order.coordinates.coeff)[0]
            residual = np.abs(line[1] - wl_fit)
            if residual <= RESIDUAL_LIMIT / 4:
                color = "black"
            elif residual <= RESIDUAL_LIMIT / 3:
                color = "#FF8C00"
            elif residual <= RESIDUAL_LIMIT / 2:
                color = "#FF4500"
            elif residual <= RESIDUAL_LIMIT:
                color = "#E63900"
            else:
                color = "red"
            ax[0].text(x=col, y=(i + 1) * inc_y_shift, s=f"({col}, {line[1]})\nresidual = {residual:.3f}", color=color)
            ax[0].axvline(col, color="red", ls="--", lw=2)
            ax[1].scatter(col, line[1], color="black", s=50)
    ax[0].set_xlim(0, 2024)
    plt.tight_layout()
    plt.show()


def fit_order_lines(comp_standard: Any, order_number: int) -> list:
    order = comp_standard.orders[order_number]
    # for compability with old file format
    order.coordinates = OrderCoordinates(
        number=order.coordinates.number, rows=order.coordinates.rows, columns=order.coordinates.columns
    )

    # normalize intensity and set its baseline to 0
    order.intensity = np.asarray(order.intensity, dtype=np.float64)
    order.intensity /= np.max(order.intensity)
    order.intensity -= np.min(order.intensity)
    order.intensity = np.asarray(order.intensity, dtype=np.float16)

    # fit the line peaks; lines whose fit does not converge are used at their listed column
    fitted_lines = []
    for line in lines.get(order_number, []):
        try:
            gauss = fit_line_with_gaussian(order.coordinates.columns, order.intensity, line[0], strict=True)
            fitted_lines.append((gauss["x0"], line[1], gauss))
        except RuntimeError:
            fitted_lines.append((line[0], line[1], []))
    return fitted_lines


def get_first_echelle_order(fitted_lines: dict[int, list]) -> int:
    """Absolute echelle order of standard order #0, from the spacing of neighbouring orders: m * l_m = (m + 1) * l_m+1."""
    centers = {}
    for order_number, order_lines in fitted_lines.items():
        if len(order_lines) >= 2:
            coeff = np.polyfit([line[0] for line in order_lines], [line[1] for line in order_lines], deg=1)
            centers[order_number] = np.polyval(coeff, COLUMN_CENTER)
    estimates = [
        centers[i + 1] / (centers[i] - centers[i + 1]) - i for i in centers if i + 1 in centers
    ]
    return int(round(np.median(estimates)))


def create_comp_standard() -> Any:
    comp_standard = load_comp_standard()
    fitted_lines = {i: fit_order_lines(comp_standard, i) for i in range(len(comp_standard.orders))}

    first_order = get_first_echelle_order(fitted_lines)
    print(f"Standard order #0 is echelle order m={first_order}")
    for i, order in enumerate(comp_standard.orders):
        order.echelle_order = first_order + i

    all_lines = [(i, line) for i, order_lines in fitted_lines.items() for line in order_lines]
    solution, keep, residuals = fit_echelle_solution(
        columns=[line[0] for _, line in all_lines],
        orders=[first_order + i for i, _ in all_lines],
        wavelengths=[line[1] for _, line in all_lines],
        free_orders=[first_order + i for i in SPLICED_ORDERS],
    )
    zero_points = [
        f"m={m}: {offset / (m * solution.wavelength(COLUMN_CENTER, m)[0]) * SPEED_OF_LIGHT:+.1f}"
        for m, offset in solution.offsets.items()
    ]
    print(
        f"2D wavelength solution from {keep.sum()}/{len(keep)} lines, rms {np.std(residuals[keep]):.3f} km/s; "
        f"zero points of spliced orders (km/s): {', '.join(zero_points)}"
    )

    kept_lines = {i: [] for i in fitted_lines}
    for (i, line), kept, residual in zip(all_lines, keep, residuals):
        if kept:
            kept_lines[i].append(line)
        else:
            removed_lines[i] = removed_lines.get(i, 0) + 1
            print(f"Order #{i}: removing line {line[1]:.4f} at column {line[0]:.1f}, residual is {residual:+.2f} km/s")

    for i, order in enumerate(comp_standard.orders):
        columns = np.asarray(order.coordinates.columns, dtype=np.float64)
        order.wavelength = solution.wavelength(columns, order.echelle_order)
        order.coordinates.coeff = chebfit(columns, order.wavelength, deg=ECHELLE_FIT_DEGREE_COLUMN)
        order.coordinates.lines = [(line[0], line[1]) for line in kept_lines[i]]
        removed_lines.setdefault(i, 0)
        if LIVE_PLOT and kept_lines[i]:
            plot_order(comp_standard, i, [line[2] for line in kept_lines[i]], order.coordinates.lines)
    comp_standard.echelle_solution = solution.to_dict()

    return comp_standard


if __name__ == "__main__":
    matplotlib.use("TkAgg")
    comp_standard = create_comp_standard()
    total = 0
    for key, value in sorted(removed_lines.items()):
        print(f"{key}:\t{value}")
        total += value
    print(f"Total: {total}")
    np.save("comp_standard.npy", comp_standard, allow_pickle=True)
