from typing import Any

import numpy as np
from numpy.polynomial.chebyshev import chebfit

from despero.echelle import EchelleSolution, fit_echelle_solution
from despero.fit import fit_line_with_gaussian, is_fit_ok
from despero.match_comp_orders import get_comp_and_standard_matching_orders
from despero.parameters import COMP_SHIFT_OUTLIER_TOLERANCE, ECHELLE_FIT_DEGREE_COLUMN
from despero.store.line import Line
from despero.store.order import Order


class CalibrationException(Exception):
    pass


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
                comp_order.coordinates.columns, comp_intensity, int(line[0] - shift), strict=True
            )
            fit_ok = is_fit_ok(line_fit_coeffs)
            is_line_peak_prominent = line_fit_coeffs["a"] >= 0.001
            if fit_ok and is_line_peak_prominent:
                lines_column.append(float(line_fit_coeffs["x0"]))
                lines_wavelength.append(line[1])

        except RuntimeError:  # gaussian fit did not converge: line not found
            continue

    # DEBUG for peak prominent filtering
    # if comp_order.coordinates.number == len(comp_order.observation.orders) - 46 - 1:
    #     import matplotlib.pyplot as plt
    #     plt.plot(comp_order.coordinates.columns, comp_intensity, color="black")
    #     for n in range(len(lines_column)):
    #         # plt.axvline(pk[n], color="pink")
    #         if pr[n]:
    #             plt.axvline(lines_column[n], ls="--", color="red")
    #         else:
    #             plt.axvline(lines_column[n], ls="--", color="blue")
    #         plt.text(x=lines_column[n]+2, y=0.5, s=f"{lines_wavelength[n]:.2f}")
    #     plt.show()
    #     import pdb; pdb.set_trace()

    return lines_column, lines_wavelength


def _set_order_wavelength(order: Order, wavelength: np.ndarray) -> None:
    order.wavelength = wavelength
    # per-order Chebyshev in column units, only for the wavelength description in the FITS header;
    # within one order the 2D solution is a polynomial of this degree, so the Chebyshev is exact
    order.coordinates.coeff = chebfit(
        np.asarray(order.coordinates.columns, dtype=np.float64), wavelength, deg=ECHELLE_FIT_DEGREE_COLUMN
    )


def calibrate_comp_spectra(comp: Any, comp_standard: Any) -> None:
    # TODO: export
    # normalize comp intensity
    for order in comp.orders:
        order.intensity = np.asarray(order.intensity, dtype=np.float16)
        order.intensity /= np.max(order.intensity)

    try:
        corresponding_apertures = get_comp_and_standard_matching_orders(comp=comp, standard=comp_standard)
    except Exception as exc:
        raise CalibrationException(f"Error calibrating ThAr spectrum {comp.fits_file.stem.split('/')[-1]}: {exc}")

    matched_orders = []  # (comp order, standard order, shift from the standard order in columns)
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
        matched_orders.append((comp_order, standard_order, comp_order.get_shift_from(standard_order)))

    # the cross-correlation fails on orders with weak lines: the shift is nearly the same for all orders,
    # so use the median shift for orders that are far from it
    median_shift = np.median([shift for _, _, shift in matched_orders])
    for i, (comp_order, standard_order, shift) in enumerate(matched_orders):
        if abs(shift - median_shift) > COMP_SHIFT_OUTLIER_TOLERANCE:
            matched_orders[i] = (comp_order, standard_order, median_shift)

    for comp_order, standard_order, shift in matched_orders:
        lines_column, lines_wavelength = _get_gaussian_fits_for_lines(
            comp_order=comp_order, standard_order=standard_order, shift=shift
        )
        comp_order.identified_lines = [
            Line(order=comp_order, column=lines_column[i], wavelength=lines_wavelength[i])
            for i in range(len(lines_column))
        ]
        comp_order.corresponding_standard_order = standard_order
        comp_order.echelle_order = standard_order.echelle_order

    lines = [(line, order.echelle_order) for order, _, _ in matched_orders for line in order.identified_lines]
    try:
        solution, keep, residuals = fit_echelle_solution(
            columns=[line.column for line, _ in lines],
            orders=[m for _, m in lines],
            wavelengths=[line.wavelength for line, _ in lines],
        )
    except ValueError as exc:
        # not enough lines for a solution of this comp: use the standard's solution, shifted per order
        standard_solution = EchelleSolution.from_dict(comp_standard.echelle_solution)
        for comp_order, _, shift in matched_orders:
            columns = np.asarray(comp_order.coordinates.columns, dtype=np.float64)
            _set_order_wavelength(comp_order, standard_solution.wavelength(columns + shift, comp_order.echelle_order))
        print(f"{comp.fits_file.name}: {exc}; using the shift-corrected standard solution")
        return

    kept_lines = {id(line) for (line, _), kept in zip(lines, keep) if kept}
    for comp_order, _, _ in matched_orders:
        columns = np.asarray(comp_order.coordinates.columns, dtype=np.float64)
        _set_order_wavelength(comp_order, solution.wavelength(columns, comp_order.echelle_order))
        n_found = len(comp_order.identified_lines)
        comp_order.identified_lines = [line for line in comp_order.identified_lines if id(line) in kept_lines]
        print(
            f"Order #{comp_order.coordinates.number} (m={comp_order.echelle_order}): "
            f"{len(comp_order.identified_lines)}/{n_found} lines used"
        )
    print(
        f"{comp.fits_file.name}: 2D wavelength solution from {keep.sum()}/{len(keep)} lines "
        f"in {len(matched_orders)} orders, rms {np.std(residuals[keep]):.3f} km/s"
    )


def get_comp_for_stellar(store: Any) -> None:
    for stellar in store.stellar:
        min_timedelta = np.inf
        for comp_index, comp in enumerate(store.comp):
            timedelta = abs(stellar.date - comp.date).total_seconds()
            if timedelta < min_timedelta:
                min_timedelta = timedelta
                stellar.comp_index = comp_index


def calibrate_stellar(stellar: Any) -> None:
    for number in range(len(stellar.orders)):
        comp = stellar.store.comp[stellar.comp_index]
        stellar.orders[number].wavelength = comp.orders[number].wavelength
