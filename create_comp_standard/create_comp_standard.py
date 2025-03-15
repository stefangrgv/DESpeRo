from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from lines import lines
from numpy.polynomial.chebyshev import chebfit, chebval

from src.fit import fit_line_with_gaussian, gaussian

LIVE_PLOT = True
GAUSS_FIT_WINDOW = 20


def plot_order(comp_standard: Any, order_number: int, gauss_params: list[dict]) -> None:
    order = comp_standard.orders[order_number]
    _, ax = plt.subplots(nrows=2, sharex=True)
    ax[0].set_title(f"Order #{order_number}")
    ax[0].plot(order.coordinates.columns, order.intensity, color="black", lw=2)
    ax[0].set_ylabel("Normalized intensity")
    ax[1].set_ylabel(r"Wavelength (${\AA}$)")
    ax[1].set_xlabel("Column number")
    order_lines = lines.get(order_number, None)
    if order_lines is not None and len(order_lines):
        # plt.rcParams.update({"font.size": 24})
        inc_y_shift = np.max(order.intensity) / (len(order_lines) + 1)
        wavelength = chebval(order.coordinates.columns, order.coordinates.coeff)
        ax[1].plot(order.coordinates.columns, wavelength, color="green", lw=2)
        coeffs = [f"{coef:.3f}" for coef in order.coordinates.coeff]
        ax[1].text(0.2, 0.8, ", ".join(coeffs), transform=ax[1].transAxes, ha="center", va="center")
        for i, line in enumerate(order_lines):
            params = gauss_params[i]
            if len(params):  # gaussian fit exists for line
                # only draw the gaussian around the line peak
                x_fit = np.linspace(params["x0"] - GAUSS_FIT_WINDOW, params["x0"] + GAUSS_FIT_WINDOW, 100)
                gauss = gaussian(x_fit, params["a"], params["x0"], params["sigma"], params["offset"])
                ax[0].axvline(params["x0"], color="red", ls="--", lw=2)
                ax[0].text(x=params["x0"], y=(i + 1) * inc_y_shift, s=f"({params['x0']:.1f}, {line[1]})", color="black")
                ax[1].scatter(params["x0"], line[1], color="black", s=50)
                ax[0].plot(x_fit, gauss, color="red", alpha=0.5, lw=2)
            else:  # no fit for the line
                ax[0].axvline(line[0], color="red", ls="--", lw=2)
                ax[0].text(x=line[0], y=(i + 1) * inc_y_shift, s=f"({line[0]}, {line[1]})", color="black")
                ax[1].scatter(line[0], line[1], color="black", s=50)
    plt.show()


def calibrate_order(comp_standard: Any, order_number: int) -> None:
    order = comp_standard.orders[order_number]

    # normalize intensity and set its baseline to 0
    order.intensity = np.asarray(order.intensity, dtype=np.float64)
    order.intensity /= np.max(order.intensity)
    order.intensity -= np.min(order.intensity)
    order.intensity = np.asarray(order.intensity, dtype=np.float16)

    order_lines = lines.get(order_number, None)
    gauss_params = []
    if order_lines is not None:
        line_columns, line_wavelengths = [], []
        for line in order_lines:
            try:
                gauss = fit_line_with_gaussian(
                    order.coordinates.columns,
                    order.intensity,
                    line[0],
                )
                gauss_params.append(gauss)
                line_columns.append(gauss["x0"])
                line_wavelengths.append(line[1])
            except RuntimeError as e:  # gaussian fit did not converge, use line without fitting
                print(e)
                gauss_params.append([])
                line_columns.append(line[0])
                line_wavelengths.append(line[1])
        order.coordinates.lines = [(line_columns[i], line_wavelengths[i]) for i in range(len(line_columns))]
        order.coordinates.coeff = chebfit(line_columns, line_wavelengths, deg=3)
    if LIVE_PLOT:
        plot_order(comp_standard, order_number, gauss_params)


def create_comp_standard() -> None:
    comp_standard = np.load("raw_comp_standard.npy", allow_pickle=True).tolist()
    for i in range(len(comp_standard.orders)):
        calibrate_order(comp_standard, i)

    return comp_standard


if __name__ == "__main__":
    matplotlib.use("TkAgg")
    comp_standard = create_comp_standard()
    np.save("../comp_standard.npy", comp_standard, allow_pickle=True)
