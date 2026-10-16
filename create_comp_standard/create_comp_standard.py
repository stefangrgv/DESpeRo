from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from lines import lines
from numpy.polynomial.chebyshev import chebfit, chebval

from despero.fit import fit_line_with_gaussian, gaussian
from despero.parameters import COMP_CALIBRATION_MIN_LINES
from despero.store.order_coordinates import OrderCoordinates
from despero.utils import load_comp_standard

LIVE_PLOT = False
GAUSS_FIT_WINDOW = 20
RESIDUAL_LIMIT = 0.01

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


def calibrate_order(comp_standard: Any, order_number: int) -> None:
    removed_lines[order_number] = 0
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

    order_lines = lines.get(order_number, None)
    if order_lines is not None:
        # fit the line peaks once; the iteration below only refits the wavelength solution
        fitted_lines = []
        for line in order_lines:
            try:
                gauss = fit_line_with_gaussian(
                    order.coordinates.columns,
                    order.intensity,
                    line[0],
                    strict=True,
                )
                fitted_lines.append((gauss["x0"], line[1], gauss))
            except RuntimeError:  # gaussian fit did not converge, use line without fitting
                fitted_lines.append((line[0], line[1], []))

        # iteration start
        while True:
            line_columns = [line[0] for line in fitted_lines]
            line_wavelengths = [line[1] for line in fitted_lines]
            deg = 1 if len(fitted_lines) <= 3 else 3
            coeff = chebfit(line_columns, line_wavelengths, deg=deg)
            residuals = np.abs(np.asarray(line_wavelengths) - chebval(line_columns, coeff))
            worst = int(np.argmax(residuals))

            if len(fitted_lines) > COMP_CALIBRATION_MIN_LINES and residuals[worst] >= RESIDUAL_LIMIT:
                # remove the worst line
                print(f"Order #{order_number}: removing line {line_wavelengths[worst]:.3f}, residual is {residuals[worst]:.3f}")
                removed_lines[order_number] = removed_lines[order_number] + 1
                fitted_lines.pop(worst)
            else:
                break

        # iteration end
        if len(fitted_lines) == deg + 1:
            # the fit passes through every line exactly, so bad lines cannot be detected
            print(f"Order #{order_number}: unchecked, only {len(fitted_lines)} lines for a deg={deg} fit")
        order.coordinates.coeff = coeff
        order.coordinates.lines = [(line[0], line[1]) for line in fitted_lines]

        if LIVE_PLOT:
            gauss_params = [line[2] for line in fitted_lines]
            plot_order(comp_standard, order_number, gauss_params, order.coordinates.lines)


def create_comp_standard() -> None:
    comp_standard = load_comp_standard()
    for i in range(len(comp_standard.orders)):
        calibrate_order(comp_standard, i)

    return comp_standard


if __name__ == "__main__":
    matplotlib.use("TkAgg")
    comp_standard = create_comp_standard()
    total = 0
    for key, value in removed_lines.items():
        print(f"{key}:\t{value}")
        total += value
    print(f"Total: {total}")
    np.save("comp_standard.npy", comp_standard, allow_pickle=True)
