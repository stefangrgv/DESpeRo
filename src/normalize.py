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


def normalize(store: Any) -> None:  # TODO: replace store with exposure
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


def stitch_oned(stellar: Any) -> None:
    all_wavelength, all_intensity, all_normalized_intensity = [], [], []

    for order_number in reversed(range(len(stellar.orders))):
        order = stellar.orders[order_number]
        all_wavelength += list(order.wavelength)
        all_intensity += list(order.intensity)
        all_normalized_intensity += list(order.normalized_intensity)

    wavelength, norm_intensity = [all_wavelength[0]], [all_normalized_intensity[0]]
    is_overlapping = False
    for i in range(1, len(all_wavelength)):
        if all_wavelength[i] > all_wavelength[i - 1]:
            if is_overlapping:
                next_overlap_wavelength.append(all_wavelength[i])
                next_overlap_intensity.append(all_intensity[i])
                next_overlap_normalized_intensity.append(all_normalized_intensity[i])
                if all_wavelength[i] > overlap_end:
                    is_overlapping = False
                    next_overlap_avg_signal = np.mean(np.asarray(next_overlap_intensity))
                    if prev_overlap_avg_signal <= next_overlap_avg_signal:
                        # next overlap has more signal, keep it and remove the prev one
                        wavelength = [
                            w for i, w in enumerate(wavelength) if i not in prev_overlap_indexes
                        ] + next_overlap_wavelength
                        norm_intensity = [
                            intensity for i, intensity in enumerate(norm_intensity) if i not in prev_overlap_indexes
                        ] + next_overlap_normalized_intensity
            else:
                wavelength.append(all_wavelength[i])
                norm_intensity.append(all_normalized_intensity[i])
        else:  # overlap just started
            next_overlap_wavelength, next_overlap_intensity, next_overlap_normalized_intensity = [], [], []
            is_overlapping = True
            wl = np.asarray(wavelength)
            overlap_end = all_wavelength[i - 1]
            overlap_start = wl[wl < all_wavelength[i]][-1]
            prev_overlap_indexes = np.where((wl >= overlap_start) & (wl <= overlap_end))[0]
            prev_overlap_avg_signal = np.mean(np.asarray(all_intensity)[prev_overlap_indexes])

    stellar.oned_wavelength = np.asarray(wavelength)
    stellar.oned_intensity = np.asarray(norm_intensity)
