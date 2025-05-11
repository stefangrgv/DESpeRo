from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from src.fit import fit_line_with_gaussian, get_finetuned_chebyshev, is_fit_ok

PLOT_SPECTRA = False  # for plot for paper

if PLOT_SPECTRA:
    from src.fit import gaussian
    from src.parameters import FIT_WINDOW_HW


def _get_useful_comp_indexes(store: Any):
    useful_indexes = [stellar.comp_index for stellar in store.stellar]
    return list(set(useful_indexes))


def calibrate_comp_spectra(store: Any) -> None:
    try:
        comp_standard = np.load("comp_standard.npy", allow_pickle=True).tolist()
    except FileNotFoundError as err:
        print("Error: comp standard not found!")
        print(err)
        exit()
    useful_comp_indexes = _get_useful_comp_indexes(store)
    for comp_index, comp in enumerate(store.comp):
        if comp_index not in useful_comp_indexes:
            continue

        for order in comp.orders:
            order.intensity = np.asarray(order.intensity, dtype=np.float16)
            order.intensity /= np.max(order.intensity)
        corresponding_apertures = []
        for standard_order in comp_standard.orders:
            deltas = np.abs([standard_order.coordinates.rows - order.rows for order in store.order_coordinates])
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
            standard_order = comp_standard.orders[i_standard]
            comp_order = comp.orders[i_comp]

            has_lines = (
                hasattr(comp_standard.orders[i_standard].coordinates, "lines")
                and len(comp_standard.orders[i_standard].coordinates.lines) > 0
            )
            # TODO: when finished, has_lines will always be true
            if has_lines:
                comp_intensity = np.asarray(comp_order.intensity, dtype=np.float16)
                comp_intensity /= np.max(comp_intensity)
                comp_intensity -= np.min(comp_intensity)
                lines_column, lines_wavelength = [], []
                for line in standard_order.coordinates.lines:
                    # plt.axvline(line[0], color="green", ls="--")
                    try:
                        line_fit_coeffs = fit_line_with_gaussian(
                            comp_order.coordinates.columns, comp_intensity, int(line[0])
                        )
                        fit_ok = is_fit_ok(line_fit_coeffs)
                        if fit_ok:
                            lines_column.append(float(line_fit_coeffs["x0"]))
                            lines_wavelength.append(line[1])

                        # TODO: remove
                        if PLOT_SPECTRA:
                            fit_x = np.linspace(
                                line[0] - 2 * FIT_WINDOW_HW, line[0] + 2 * FIT_WINDOW_HW, 20 * FIT_WINDOW_HW
                            )
                            line_fit = gaussian(
                                fit_x,
                                line_fit_coeffs["a"],
                                line_fit_coeffs["x0"],
                                line_fit_coeffs["sigma"],
                                line_fit_coeffs["offset"],
                            )
                            if fit_ok:
                                color = "purple"
                            else:
                                color = "orange"
                            plt.plot(fit_x, line_fit, color=color, label="gaussian fit")
                            plt.axvline(line_fit_coeffs["x0"], color=color, ls="--")

                    except RuntimeError:  # gaussian fit did not converge: line not found
                        continue
                # TODO: remove
                if PLOT_SPECTRA:
                    plt.plot(comp_order.coordinates.columns, comp_order.intensity, color="black", label="comp")
                    plt.plot(
                        standard_order.coordinates.columns, standard_order.intensity, color="red", label="standard"
                    )
                    plt.legend()
                    plt.show()
                cheby_fit = get_finetuned_chebyshev(lines_column, lines_wavelength, standard_order.coordinates.coeff)
                comp_order.coordinates.coeff = cheby_fit.coef
                comp_order.wavelength = cheby_fit(np.asarray(comp_order.coordinates.columns))


def get_comp_for_stellar(store: Any) -> None:
    for stellar in store.stellar:
        min_timedelta = np.inf
        for comp_index, comp in enumerate(store.comp):
            timedelta = abs(stellar.date - comp.date).total_seconds()
            if timedelta < min_timedelta:
                min_timedelta = timedelta
                stellar.comp_index = comp_index


def calibrate_stellar(store: Any) -> None:
    for stellar in store.stellar:
        for order_number in range(len(stellar.orders)):
            comp = store.comp[stellar.comp_index]
            stellar.orders[order_number].wavelength = comp.orders[order_number].wavelength
