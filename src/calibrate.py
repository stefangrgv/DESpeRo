import os
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate

from src.fit import find_line_peak, gaussian
from src.parameters import CUTOFF

PLOT_SPECTRA = False
EXPORT_SPECTRA = True


def fit_chebyshev(points: list[int, float], degree: int = 3) -> np.ndarray:
    px, wl = ([], [])
    for p in points:
        px.append(p[0])
        wl.append(p[1])
    return np.polynomial.chebyshev.Chebyshev.fit(px, wl, deg=degree)


def _get_comp_shift_from_standard(standard_intensity: float, comp_intensity: float) -> int:
    correlation = correlate(comp_intensity, standard_intensity, mode="full")
    return np.argmax(correlation) - len(comp_intensity) + 1


def calibrate_comp_spectra(store: Any) -> None:
    try:
        comp_standard = np.load("comp_standard.npy", allow_pickle=True).tolist()
    except FileNotFoundError as err:
        print("Error: comp standard not found!")
        print(err)
        sys.exit(1)
    for comp in store.comp:
        comp_filename = comp.fits_file.split("/")[-1].split(".fits")[0]
        print(f"Calibrating comp spectrum {comp_filename}...")
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
            has_points = (
                hasattr(comp_standard.orders[i_standard].order_coordinates, "points")
                and len(comp_standard.orders[i_standard].order_coordinates.points) > 0
            )
            # TODO: when finished, has_points will always be true
            if has_points:
                comp_intensity = np.asarray(comp.orders[i_comp].intensity, dtype=np.float16)
                comp_intensity /= np.max(comp_intensity)
                pixel_shift = _get_comp_shift_from_standard(comp_standard.orders[i_standard].intensity, comp_intensity)
                comp_points = []
                for point in comp_standard.orders[i_standard].order_coordinates.points:
                    # plt.axvline(point[0], color="green", ls="--")
                    line_fit_coeffs = find_line_peak(
                        comp.orders[i_comp].order_coordinates.columns, comp_intensity, int(point[0] - CUTOFF)
                    )
                    fit_x = np.linspace(0, 2048, 2048 * 16)
                    line_fit = gaussian(
                        fit_x,
                        line_fit_coeffs["a"],
                        line_fit_coeffs["x0"],
                        line_fit_coeffs["sigma"],
                        line_fit_coeffs["offset"],
                    )
                    comp_points.append((float(line_fit_coeffs["x0"]), point[1]))
                #     plt.plot(fit_x, line_fit, color="purple", label="gaussian fit")
                #     plt.axvline(line_fit_coeffs["x0"], color="purple", ls="--")
                # plt.legend()
                # plt.show()
                cheby_fit = fit_chebyshev(comp_points, degree=3)
                comp.orders[i_comp].wavelength = cheby_fit(np.asarray(comp.orders[i_comp].columns))


def _draw_comp_for_journal(
    comp_standard: Any,
    comp: Any,
    i_standard: int,
    i_comp: int,
    has_points: bool,
    order_shift: int,
    comp_filename: str,
) -> None:
    plt.title(f"i_standard = {i_standard}, i_comp = {i_comp}")
    plt.plot(
        comp_standard.orders[i_standard].order_coordinates.columns,
        comp_standard.orders[i_standard].intensity,
        color="black",
        label="standard",
        alpha=0.5,
    )
    plt.plot(
        comp.orders[i_comp].order_coordinates.columns,
        comp.orders[i_comp].intensity,
        color="green",
        label="comp",
        alpha=0.5,
    )
    if has_points:
        for point in comp_standard[i_standard]["order_coordinates"]["points"]:
            plt.axvline(point[0], color="red", ls="--")
            # TODO: y should have an increment
            plt.text(
                x=point[0] + order_shift,
                y=np.max(comp.orders[i_comp].intensity) / 2,
                s=f"{point[1]}",
                color="red",
                alpha=0.5,
            )
    plt.legend()
    os.makedirs(f"comp/{comp_filename}", exist_ok=True)
    # plt.savefig(f"comp/{comp_filename}/order_{i_standard}.png", dpi=500)
    plt.show()
    plt.cla()
    plt.clf()
    plt.close()


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
