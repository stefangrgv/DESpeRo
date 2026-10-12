from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from lines import lines
from numpy.polynomial.chebyshev import chebfit, chebval

from despero.fit import fit_line_with_gaussian, gaussian
from despero.store.order_coordinates import OrderCoordinates
from despero.utils import load_comp_standard

LIVE_PLOT = False
GAUSS_FIT_WINDOW = 20
RESIDUAL_LIMIT = 0.005

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

    # iteration start
    if order_lines is not None:
        while True:
            gauss_params = []
            line_columns, line_wavelengths = [], []
            for line in order_lines:
                try:
                    gauss = fit_line_with_gaussian(
                        order.coordinates.columns,
                        order.intensity,
                        line[0],
                        strict=True,
                    )
                    gauss_params.append(gauss)
                    line_columns.append(gauss["x0"])
                    line_wavelengths.append(line[1])
                except RuntimeError as e:  # gaussian fit did not converge, use line without fitting
                    # print(e)
                    gauss_params.append([])
                    line_columns.append(line[0])
                    line_wavelengths.append(line[1])
            order_lines = [(line_columns[i], line_wavelengths[i]) for i in range(len(line_columns))]

            # if order_number in [1, 61, 62, 63]:
            if len(order_lines) <= 3:
                coeff = chebfit(line_columns, line_wavelengths, deg=1)
            else:
                coeff = chebfit(line_columns, line_wavelengths, deg=3)

            lines_with_residuals = []
            for line in order_lines:
                wl_known = line[1]
                wl_fit = chebval([line[0]], coeff)[0]
                resiudal = np.abs(wl_known - wl_fit)
                lines_with_residuals.append([line, resiudal])

            lines_with_residuals.sort(key=lambda x: x[1])

            if len(lines_with_residuals) >= 3 and lines_with_residuals[-1][1] >= RESIDUAL_LIMIT:
                # remove the worst line
                print(f"Order #{order_number}: removing line {lines_with_residuals[-1][0][1]:.3f}, residual is {lines_with_residuals[-1][1]:.3f}")
                removed_lines[order_number] = removed_lines[order_number] + 1
                order_lines = [line for line, _ in lines_with_residuals[0:-1]]
            else:
                break

        # iteration end
        order.coordinates.coeff = coeff
        order.coordinates.lines = order_lines
            
        if LIVE_PLOT:
            plot_order(comp_standard, order_number, gauss_params, order_lines)


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
    np.save("residualized_comp_standard.npy", comp_standard, allow_pickle=True)
