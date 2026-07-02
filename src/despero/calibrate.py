from typing import Any

import numpy as np

from despero.fit import (fit_line_with_gaussian, get_finetuned_chebyshev,
                         is_fit_ok)
from despero.match_comp_orders import get_comp_and_standard_matching_orders
from despero.store.line import Line
from despero.store.order import Order


def get_useful_comp_indexes(store: Any):
    useful_indexes = [stellar.comp_index for stellar in store.stellar]
    return list(set(useful_indexes))


def _get_gaussian_fits_for_lines(comp_order: Order, standard_order: Order, shift: float):
    comp_intensity = np.asarray(comp_order.intensity, dtype=np.float16)
    comp_intensity /= np.max(comp_intensity)
    comp_intensity -= np.min(comp_intensity)

    lines_column, lines_wavelength = [], []
    for line in standard_order.coordinates.lines:
        if line[0] - shift <= 0:
            # line outside of spectrum
            continue
        try:
            line_fit_coeffs = fit_line_with_gaussian(
                comp_order.coordinates.columns, comp_intensity, int(line[0] - shift)
            )
            fit_ok = is_fit_ok(line_fit_coeffs)
            if fit_ok:
                lines_column.append(float(line_fit_coeffs["x0"]))
                lines_wavelength.append(line[1])

        except RuntimeError:  # gaussian fit did not converge: line not found
            continue

    return lines_column, lines_wavelength


def calibrate_comp_spectra(comp: Any, comp_standard: Any) -> None:
    # TODO: export
    # normalize comp intensity
    for order in comp.orders:
        order.intensity = np.asarray(order.intensity, dtype=np.float16)
        order.intensity /= np.max(order.intensity)

    corresponding_apertures = get_comp_and_standard_matching_orders(comp=comp, standard=comp_standard)
    for order_pair in corresponding_apertures:
        i_comp, i_standard = order_pair
        if i_standard >= len(comp_standard.orders):
            # standard does not have that many orders, ignore
            continue
        if i_comp >= len(comp.orders):
            # comp does not have that many orders, ignore
            continue
        standard_order = comp_standard.orders[i_standard]
        comp_order = comp.orders[i_comp]
        # TODO: _get_shift must be a method of Order, and take another order as argument
        shift = _get_shift(
            comp_order.coordinates.columns,
            comp_order.intensity,
            standard_order.intensity,
        )
        lines_column, lines_wavelength = _get_gaussian_fits_for_lines(
            comp_order=comp_order, standard_order=standard_order, shift=shift
        )
        comp_order.identified_lines = [
            Line(order=comp_order, column=lines_column[i], wavelength=lines_wavelength[i])
            for i in range(len(lines_column))
        ]
        comp_order.corresponding_standard_order = standard_order
        if len(comp_order.identified_lines) > 0:
            cheby_fit = get_finetuned_chebyshev(lines_column, lines_wavelength, standard_order.coordinates.coeff)
            comp_order.coordinates.coeff = cheby_fit.coef
            comp_order.wavelength = cheby_fit(np.asarray(comp_order.coordinates.columns))


def _get_shift(x1, y1, y2):
    from scipy.signal import correlate

    y1c = y1 - np.mean(y1)
    y2c = y2 - np.mean(y2)

    corr = correlate(y2c, y1c, mode="full")

    lags = np.arange(-len(y1) + 1, len(y1))

    best_lag = lags[np.argmax(corr)]

    dx = best_lag * (x1[1] - x1[0])

    return dx


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
