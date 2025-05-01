from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.signal import find_peaks


def _fit_continuum(
    wavelength: list[float] | np.ndarray,
    intensity: list[float],
) -> np.ndarray:
    intensity_array = np.asarray(intensity)
    peaks_ind, _ = find_peaks(intensity_array)
    cheby_fit = np.polynomial.chebyshev.Chebyshev.fit(wavelength[peaks_ind], intensity_array[peaks_ind], deg=5)
    return cheby_fit(wavelength)


def normalize(store: Any) -> None:
    print("Normalizing intensity...")
    for stellar in store.stellar:
        for i, order in enumerate(stellar.orders):
            if len(order.wavelength):
                try:
                    continuum = _fit_continuum(order.wavelength, order.intensity)
                    stellar.orders[i].normalized_intensity = order.intensity / continuum
                except Exception as e:
                    print(f"\tCould not normalize order #{i}: {e}")


@dataclass
class Overlap:
    wl_start: float
    wl_end: float
    n_order_1: int
    n_order_2: int
    observation: Any

    def keep_end_of_first_order(self):
        """
        Returns true if the end of the first order will be kept, false otherwise
        """

        first_order = self.observation.orders[self.n_order_1]
        second_order = self.observation.orders[self.n_order_2]
        indexes_1 = np.where((first_order.wavelength >= self.wl_start) & (first_order.wavelength <= self.wl_end))[0]
        intensity_1 = np.asarray(first_order.intensity)[indexes_1]
        indexes_2 = np.where((second_order.wavelength >= self.wl_start) & (second_order.wavelength <= self.wl_end))[0]
        intensity_2 = np.asarray(second_order.intensity)[indexes_2]

        return np.sum(intensity_1) >= np.sum(intensity_2)


def stitch_oned(store: Any) -> None:
    print("Building 1D spectra...")
    for stellar in store.stellar:
        try:
            oned_wavelength, oned_intensity = [], []

            overlaps = []
            for order_number in reversed(range(len(stellar.orders))):
                order = stellar.orders[order_number]
                if order_number < len(stellar.orders) - 1:
                    next_order = stellar.orders[order_number + 1]
                else:
                    next_order = None

                if next_order is not None and order.wavelength[-1] >= next_order.wavelength[0]:
                    # has overlap
                    overlap = Overlap(
                        wl_start=order.wavelength[0],
                        wl_end=next_order.wavelength[-1],
                        n_order_1=order_number,
                        n_order_2=order_number + 1,
                        observation=stellar,
                    )
                    keep_end = overlap.keep_end_of_first_order()

                    # check if the start of the current order should be kept
                    keep_start = True
                    previous_overlap = None
                    for ol in overlaps:
                        if ol.n_order_1 == order_number + 1:
                            if ol.keep_end_of_first_order():
                                keep_start = False
                                previous_overlap = ol
                                break
                    overlaps.append(overlap)

                    if keep_start:
                        indexes_start = np.arange(len(order.wavelength))
                    else:
                        indexes_start = np.where(
                            (order.wavelength < previous_overlap.wl_start)
                            | (order.wavelength > previous_overlap.wl_end)
                        )[0]

                    if keep_end:
                        indexes_end = np.arange(len(order.wavelength))
                    else:
                        indexes_end = np.where(
                            (order.wavelength < overlap.wl_start) | (order.wavelength > overlap.wl_end)
                        )[0]
                        if len(indexes_end) == 0:
                            import pdb

                            pdb.set_trace()

                    keep_indexes = np.intersect1d(indexes_start, indexes_end)
                    oned_wavelength += list(order.wavelength[keep_indexes])
                    oned_intensity += list(order.normalized_intensity[keep_indexes])
                else:
                    # no overlap
                    oned_wavelength += list(order.wavelength)
                    oned_intensity += list(order.normalized_intensity)

            stellar.oned_wavelength = np.asarray(oned_wavelength)
            stellar.oned_intensity = np.asarray(oned_intensity)
        except Exception as exc:
            print(f"Error: cannot create 1D spectrum for {stellar.fits_file}: {exc}")
