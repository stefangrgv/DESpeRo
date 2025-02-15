import os
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate

from src.fit import fit_line_with_gaussian, gaussian
from src.parameters import CUTOFF

PLOT_SPECTRA = False  # for plot for paper


def fit_chebyshev(lines: list[int, float], degree: int = 3) -> np.ndarray:
    px, wl = ([], [])
    for p in lines:
        px.append(p[0])
        wl.append(p[1])
    return np.polynomial.chebyshev.Chebyshev.fit(px, wl, deg=degree)


def _get_comp_shift_from_standard(standard_intensity: float, comp_intensity: float) -> int:
    correlation = correlate(comp_intensity, standard_intensity, mode="full")
    return np.argmax(correlation) - len(comp_intensity) + 1


def calibrate_comp_spectra(store: Any) -> None:
    print(f"Calibrating comp spectra...")
    try:
        comp_standard = np.load("comp_standard.npy", allow_pickle=True).tolist()
    except FileNotFoundError as err:
        print("Error: comp standard not found!")
        print(err)
        sys.exit(1)
    for comp in store.comp:
        for order_number in range(len(comp.orders)):
            comp.orders[order_number].intensity = np.asarray(comp.orders[order_number].intensity, dtype=np.float16)
            comp.orders[order_number].intensity /= np.max(comp.orders[order_number].intensity)
        corresponding_apertures = []
        for standard_order in comp_standard.orders:
            deltas = np.abs(
                [standard_order.order_coordinates.rows - order.order_coordinates.rows for order in comp.orders]
            )
            min_delta_index = np.argmin([np.sum(delta) for delta in deltas])
            corresponding_apertures.append(min_delta_index)
        order_shift = np.median(
            np.linspace(0, len(comp_standard.orders) - 1, len(comp_standard.orders))
            - np.asarray(corresponding_apertures)
        ).astype(int)
        for i_standard in range(len(comp_standard.orders)):
            if i_standard != corresponding_apertures[i_standard] + order_shift:
                # Order does not match any order in the comparison standard - will be ignored
                continue
            i_comp = i_standard - order_shift
            has_lines = (
                hasattr(comp_standard.orders[i_standard].order_coordinates, "lines")
                and len(comp_standard.orders[i_standard].order_coordinates.lines) > 0
            )
            # TODO: when finished, has_lines will always be true
            if has_lines:
                comp_intensity = np.asarray(comp.orders[i_comp].intensity, dtype=np.float16)
                comp_intensity /= np.max(comp_intensity)
                comp_intensity -= np.min(comp_intensity)
                pixel_shift = _get_comp_shift_from_standard(comp_standard.orders[i_standard].intensity, comp_intensity)
                comp_lines = []
                for line in comp_standard.orders[i_standard].order_coordinates.lines:
                    # plt.axvline(line[0], color="green", ls="--")
                    try:
                        line_fit_coeffs = fit_line_with_gaussian(
                            comp.orders[i_comp].order_coordinates.columns, comp_intensity, int(line[0])
                        )
                        fit_x = np.linspace(0, 2048, 2048 * 16)
                        line_fit = gaussian(
                            fit_x,
                            line_fit_coeffs["a"],
                            line_fit_coeffs["x0"],
                            line_fit_coeffs["sigma"],
                            line_fit_coeffs["offset"],
                        )
                        comp_lines.append((float(line_fit_coeffs["x0"]), line[1]))
                    except RuntimeError:  # gaussian fit did not converge: line not found
                        continue
                #     plt.plot(fit_x, line_fit, color="purple", label="gaussian fit")
                #     plt.axvline(line_fit_coeffs["x0"], color="purple", ls="--")
                # plt.legend()
                # plt.show()
                cheby_fit = fit_chebyshev(comp_lines, degree=3)
                comp.orders[i_comp].wavelength = cheby_fit(np.asarray(comp.orders[i_comp].columns))


def get_comp_for_stellar(store: Any) -> None:
    for stellar in store.stellar:
        min_timedelta = np.inf
        for comp in store.comp:
            timedelta = abs(stellar.date - comp.date).total_seconds()
            if timedelta < min_timedelta:
                min_timedelta = timedelta
                stellar.comp = comp


def calibrate_stellar(store: Any) -> None:
    for stellar in store.stellar:
        fname = stellar.fits_file.split(".fits")[0]
        print(f"Calibrating for lambda: {stellar.fits_file}...")
        for order_number in range(len(stellar.orders)):
            stellar.orders[order_number].wavelength = stellar.comp.orders[order_number].wavelength
            if len(stellar.comp.orders[order_number].wavelength) and PLOT_SPECTRA:
                os.makedirs(f"stellar/{fname}", exist_ok=True)
                plt.plot(stellar.orders[order_number].wavelength, stellar.orders[order_number].intensity)
                plt.savefig(f"stellar/{fname}/{str(order_number)}.eps")
                plt.clf()
                plt.cla()
