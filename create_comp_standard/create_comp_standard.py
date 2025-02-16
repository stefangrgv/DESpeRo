import os
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from lines import lines

from pyraf import iraf
from src.apall import extract_2d_spectra, find_orders_coordinates
from src.calibrate import fit_chebyshev
from src.fit import fit_line_with_gaussian, gaussian
from src.initial_corrections import correct_for_bias, correct_for_flat
from src.store.store import Store

LIVE_PLOT = True
GAUSS_FIT_WINDOW = 20

CORRECT_BIAS = False
CORRECT_FLAT = False

matplotlib.use("TkAgg")
load_dotenv()


def plot_order(comp_standard: Any, order_number: int, gauss_params: list[dict]) -> None:
    order = comp_standard.orders[order_number]
    _, ax = plt.subplots(nrows=2, sharex=True)
    ax[0].set_title(f"Order #{order_number}")
    ax[0].plot(order.order_coordinates.columns, order.intensity, color="black", lw=2)
    ax[0].set_ylabel("Normalized intensity")
    ax[1].set_ylabel(r"Wavelength (${\AA}$)")
    ax[1].set_xlabel("Column number")
    order_lines = lines.get(order_number, None)
    if order_lines is not None and len(order_lines):
        # plt.rcParams.update({"font.size": 24})
        inc_y_shift = np.max(order.intensity) / (len(order_lines) + 1)
        cheby_fit = fit_chebyshev(order_lines, degree=3)
        order.wavelength = cheby_fit(order.order_coordinates.columns)
        ax[1].plot(order.order_coordinates.columns, order.wavelength, color="green", lw=2)
        coeffs = [f"{coef:.2f}" for coef in cheby_fit.coef]
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
    comp_standard.orders[order_number].intensity = np.asarray(
        comp_standard.orders[order_number].intensity, dtype=np.float16
    )
    comp_standard.orders[order_number].intensity /= np.max(comp_standard.orders[order_number].intensity)
    comp_standard.orders[order_number].intensity -= np.min(comp_standard.orders[order_number].intensity)
    order_lines = lines.get(order_number, None)
    if order_lines is not None:
        exact_line_positions = []
        gauss_params = []
        for line in order_lines:
            try:
                gauss = fit_line_with_gaussian(
                    comp_standard.orders[order_number].order_coordinates.columns,
                    comp_standard.orders[order_number].intensity,
                    line[0],
                )
                gauss_params.append(gauss)
                exact_line_positions.append((gauss["x0"], line[1]))
            except RuntimeError as e:  # gaussian fit did not converge, use line without fitting
                print(e)
                gauss_params.append([])
                exact_line_positions.append((line[0], line[1]))
        comp_standard.orders[order_number].order_coordinates.lines = exact_line_positions
        if LIVE_PLOT:
            plot_order(comp_standard, order_number, gauss_params)


def create_comp_standard() -> None:
    directory = os.getenv("COMP_STANDARD_DIR") or input("Enter path to observations directory: ")
    store = Store(directory)
    store.load_journal_from_file()

    if CORRECT_BIAS or CORRECT_FLAT:
        iraf.noao()
        iraf.rv()
        iraf.imred()
        iraf.ccd()

    if CORRECT_BIAS:
        # TODO: do more tests to make sure bias correction works as intended
        store.create_master_biases()
        correct_for_bias(store)

    if CORRECT_FLAT:
        store.create_master_flats()
        find_orders_coordinates(store, use_master_flat=True, draw=True)
        correct_for_flat(store)
    else:
        find_orders_coordinates(store, use_master_flat=False, draw=True)
    extract_2d_spectra(store, store.comp)

    comp_standard = store.comp[0]
    for i in range(len(comp_standard.orders)):
        calibrate_order(comp_standard, i)

    comp_standard.raw_data = None  # raw data is not needed for calibration
    return comp_standard


if __name__ == "__main__":
    comp_standard = create_comp_standard()
    np.save("../comp_standard.npy", comp_standard, allow_pickle=True)
