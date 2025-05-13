from typing import Any

import numpy as np

from src.fit import fit_line_with_gaussian, get_finetuned_chebyshev, is_fit_ok


def get_useful_comp_indexes(store: Any):
    useful_indexes = [stellar.comp_index for stellar in store.stellar]
    return list(set(useful_indexes))


def calibrate_comp_spectra(comp: Any, comp_standard: Any) -> None:
    for order in comp.orders:
        order.intensity = np.asarray(order.intensity, dtype=np.float16)
        order.intensity /= np.max(order.intensity)
    corresponding_apertures = []
    for standard_order in comp_standard.orders:
        deltas = np.abs([standard_order.coordinates.rows - order.rows for order in comp.store.order_coordinates])
        min_delta_index = np.argmin([np.sum(delta) for delta in deltas])
        corresponding_apertures.append(min_delta_index)
    order_shift = np.median(
        np.linspace(0, len(comp_standard.orders) - 1, len(comp_standard.orders)) - np.asarray(corresponding_apertures)
    ).astype(int)
    for i_standard in range(len(comp_standard.orders)):
        if i_standard != corresponding_apertures[i_standard] + order_shift:
            # Order does not match any order in the comparison standard - will be ignored
            continue
        i_comp = i_standard - order_shift
        standard_order = comp_standard.orders[i_standard]
        comp_order = comp.orders[i_comp]
        comp_intensity = np.asarray(comp_order.intensity, dtype=np.float16)
        comp_intensity /= np.max(comp_intensity)
        comp_intensity -= np.min(comp_intensity)
        lines_column, lines_wavelength = [], []
        for line in standard_order.coordinates.lines:
            try:
                line_fit_coeffs = fit_line_with_gaussian(comp_order.coordinates.columns, comp_intensity, int(line[0]))
                fit_ok = is_fit_ok(line_fit_coeffs)
                if fit_ok:
                    lines_column.append(float(line_fit_coeffs["x0"]))
                    lines_wavelength.append(line[1])

            except RuntimeError:  # gaussian fit did not converge: line not found
                continue
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


def calibrate_stellar(stellar: Any) -> None:
    for order_number in range(len(stellar.orders)):
        comp = stellar.store.comp[stellar.comp_index]
        stellar.orders[order_number].wavelength = comp.orders[order_number].wavelength
