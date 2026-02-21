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


def normalize(observation: Any) -> None:
    for i, order in enumerate(observation.orders):
        if len(order.wavelength):
            try:
                continuum = _fit_continuum(order.wavelength, order.intensity)
                observation.orders[i].normalized_intensity = order.intensity / continuum
            except Exception as e:
                print(f"\tCould not normalize order #{i}: {e}")
                observation.orders[i].normalized_intensity = [np.NAN for _ in order.intensity]


def stitch_oned(stellar: Any) -> None:
    reversed_orders = list(reversed(stellar.orders))  # in growing wavelength (blue ones first)
    wavelength = []
    intensity = []  # to keep track of the SNR
    n_intensity = []
    for order in reversed_orders:
        if len(wavelength) == 0 or order.wavelength[0] > wavelength[-1]:
            # no overlap
            wavelength = [*wavelength, *list(order.wavelength)]
            intensity = [*intensity, *list(order.intensity)]
            n_intensity = [*n_intensity, *list(order.normalized_intensity)]
        else:
            overlap_prev_ind = np.where(wavelength >= order.wavelength[0])[0]
            overlap_next_ind = np.where(order.wavelength <= wavelength[-1])[0]
            overlap_prev_signal = [intensity[i] for i in overlap_prev_ind]
            overlap_next_signal = [order.intensity[i] for i in overlap_next_ind]
            if np.mean(overlap_prev_signal) > np.mean(overlap_next_signal):
                # previous (bluer) order has more signal
                wavelength = [*wavelength, *list(order.wavelength[overlap_next_ind[-1] :])]
                intensity = [*intensity, *list(order.intensity[overlap_next_ind[-1] :])]
                n_intensity = [*n_intensity, *list(order.normalized_intensity[overlap_next_ind[-1] :])]
            else:
                keep_ind = [i for i in range(len(wavelength)) if i not in overlap_prev_ind]
                wavelength = [*[wavelength[i] for i in keep_ind], *list(order.wavelength)]
                intensity = [*[intensity[i] for i in keep_ind], *list(order.intensity)]
                n_intensity = [*[n_intensity[i] for i in keep_ind], *list(order.normalized_intensity)]

    stellar.oned_wavelength = np.asarray(wavelength)
    stellar.oned_intensity = np.asarray(n_intensity)
