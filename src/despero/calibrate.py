from typing import Any

import numpy as np
from numpy.polynomial.chebyshev import chebfit, chebval

from despero.fit import (fit_line_with_gaussian, get_finetuned_chebyshev,
                         is_fit_ok)
from despero.match_comp_orders import get_comp_and_standard_matching_orders
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
                comp_order.coordinates.columns, comp_intensity, int(line[0] - shift)
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

    # return lines_column, lines_wavelength


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
        shift = comp_order.get_shift_from(standard_order)
        lines_column, lines_wavelength = _get_gaussian_fits_for_lines(
            comp_order=comp_order, standard_order=standard_order, shift=shift
        )
        comp_order.identified_lines = [
            Line(order=comp_order, column=lines_column[i], wavelength=lines_wavelength[i])
            for i in range(len(lines_column))
        ]
        comp_order.corresponding_standard_order = standard_order
        if len(comp_order.identified_lines) >= 2:
            n_lines = len(lines_column)
            if n_lines >= 3:
                cheby_fit = get_finetuned_chebyshev(lines_column, lines_wavelength, standard_order.coordinates.coeff)
                comp_order.coordinates.coeff = cheby_fit.coef
                comp_order.wavelength = cheby_fit(np.asarray(comp_order.coordinates.columns))
            # if there are fewer than 3 lines in the comp, don't try to fit a cheby with deg=3, even if the standard has it
            else:
                coeff = chebfit(lines_column, lines_wavelength, deg=1)
                comp_order.coordinates.coeff = coeff
                comp_order.wavelength = chebval(np.asarray(comp_order.coordinates.columns), coeff)
        else:  # not enough lines to get a solution: use the shift-corrected standard instead
            lines_column = [line.column - shift for line in standard_order.identified_lines if line.column >= shift]
            lines_wavelength = [line.wavelength for line in standard_order.identified_lines if line.column >= shift]
            n_lines = len(lines_column)
            if n_lines > 0:
                deg = 3 if n_lines > 2 else 1
                coeff = chebfit(lines_column, lines_wavelength, deg=deg)
                comp_order.coordinates.coeff = coeff
                comp_order.wavelength = chebval(np.asarray(comp_order.coordinates.columns), coeff)

        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots(nrows=3, sharex=True)
        # ax[2].plot(standard_order.coordinates.columns, standard_order.intensity, color="purple")
        # for line in standard_order.identified_lines:
        #     ax[2].axvline(line.column, color='red', ls='--')
        #     ax[2].text(x=line.column + 2, y=2*np.mean(standard_order.intensity), s=f"{line.wavelength:.2f}")
        # ax[1].plot(comp_order.coordinates.columns, comp_order.intensity, color="black")
        # for line in comp_order.identified_lines:
        #     ax[1].axvline(line.column, color='red', ls='--')
        #     ax[1].text(x=line.column + 2, y=2*np.mean(comp_order.intensity), s=f"{line.wavelength:.2f}")
        # try:
        #     ax[0].set_title(f"Order {i_comp}: {int(comp_order.wavelength[0])}:{int(comp_order.wavelength[-1])}")
        # except Exception:
        #     ax[0].set_title(f"Order {i_comp}")
        # try:
        #     ax[0].plot(comp_order.coordinates.columns, comp_order.wavelength, color="black")
        # except Exception:
        #     print("no wavelength solution")
        # print(comp_order.coordinates.coeff)
        # plt.show()


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
