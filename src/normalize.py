from typing import Any

import numpy as np


def _fit_continuum(
    wavelength: list[float] | np.ndarray,
    intensity: list[float],
    absorption_threshold: int = 60,
    emission_threshold: int = 90,
) -> np.ndarray:
    intensity = np.asarray(intensity)
    n = len(wavelength)
    parts_to_split_into = 6
    large_part_fraction = 1 / (parts_to_split_into - 1)
    parts_index_ranges = []
    for i in range(parts_to_split_into):
        if i == 0:
            parts_index_ranges.append([0, int((large_part_fraction / 2) * n)])
        elif i == parts_to_split_into - 1:
            start = parts_index_ranges[-1][1]
            parts_index_ranges.append([start])
        else:
            start = parts_index_ranges[-1][1]
            end = int(start + large_part_fraction * n)
            parts_index_ranges.append([start, end])
    part_indexes = [np.asarray([i for i in range(part[0], part[1])]) for part in parts_index_ranges]
    continuum_indices = []
    for part_number in range(len(parts_index_ranges)):
        (ind_start, ind_end) = parts_index_ranges[part_number]
        intensity_part = intensity[ind_start:ind_end]
        lower_threshold = np.percentile(intensity_part, absorption_threshold)
        upper_threshold = np.percentile(intensity_part, emission_threshold)
        continuum_mask = (intensity_part > lower_threshold) & (intensity_part < upper_threshold)
        continuum_indices += part_indexes[part_number][continuum_mask].tolist()
    continuum_wavelength = wavelength[continuum_indices]
    continuum_intensity = intensity[continuum_indices]
    cheby_fit = np.polynomial.chebyshev.Chebyshev.fit(continuum_wavelength, continuum_intensity, deg=5)
    return cheby_fit(wavelength)


def normalize(store: Any) -> None:
    for stellar in store.stellar:
        print(f"Normalizing {stellar.fits_file}...")
        for i, order in enumerate(stellar.orders):
            try:
                continuum = _fit_continuum(order.wavelength, order.intensity)
                order.normalized_intensity = order.intensity / continuum
            except Exception as e:
                print(f"\tCould not normalize order #{i}: {e}")


def stitch_oned(store: Any) -> None:
    for s, stellar in enumerate(store.stellar):
        print(f"Stitching {stellar.fits_file}...")
        (oned_wavelength, oned_intensity) = ([], [])
        # this is a BAD algorithm even if it works, it's really slow
        # stack the orders together: all_wl = [*wl for wl in order.wavelength for order in stellar.orders], same for intensity
        # iterate over the spectrum and save good results in a wl array, same for intensity
        # but first of all, fix the calibration
        for i, order in enumerate(stellar.orders[13:45]):
            if len(order.normalized_intensity) == 0:
                print("\tCould not create 1D spectrum: some orders are not normalized!")
                break
            next_order = stellar.orders[i + 1]
            # find the overlapping (ol) wavelength window
            ol_start = next_order.wavelength[-1]
            ol_end = order.wavelength[0]
            if ol_start < ol_end:  # overlap exists
                order_ol_indexes = [j for j in range(len(order.wavelength)) if order.wavelength[j] >= ol_start]
                next_order_ol_indexes = [
                    j for j in range(len(next_order.wavelength)) if next_order.wavelength[j] <= ol_end
                ]
                # add points outside the overlap for the current order
                for j in range(len(order.wavelength)):
                    if j not in order_ol_indexes and order.wavelength[j] not in oned_wavelength:
                        oned_wavelength.append(order.wavelength[j])
                        oned_intensity.append(order.normalized_intensity[j])
                # add points inside the overlap for the order with the higher SNR
                if np.sum([order.intensity[j] for j in order_ol_indexes]) >= np.sum(
                    [next_order.intensity[j] for j in next_order_ol_indexes]
                ):
                    for j in range(len(order.wavelength)):
                        if j in order_ol_indexes and order.wavelength[j] not in oned_wavelength:
                            oned_wavelength.append(order.wavelength[j])
                            oned_intensity.append(order.normalized_intensity[j])
                else:
                    for j in range(len(next_order.wavelength)):
                        if j in next_order_ol_indexes and next_order.wavelength[j] not in oned_wavelength:
                            oned_wavelength.append(next_order.wavelength[j])
                            oned_intensity.append(next_order.normalized_intensity[j])
                # add points outside the overlap for the next order
                for j in range(len(next_order.wavelength)):
                    if j not in next_order_ol_indexes and next_order.wavelength[j] not in oned_wavelength:
                        oned_wavelength.append(next_order.wavelength[j])
                        oned_intensity.append(next_order.normalized_intensity[j])
            else:  # no overlap
                for j in range(len(order.wavelength)):
                    if order.wavelength[j] not in oned_wavelength:
                        oned_wavelength.append(order.wavelength[j])
                        oned_intensity.append(order.normalized_intensity[j])
        # do something with the two arrays
        store.stellar[s].oned_wavelength = np.asarray(oned_wavelength, dtype=np.float32)
        store.stellar[s].oned_intensity = np.asarray(oned_intensity, dtype=np.float32)
        print(np.min(oned_wavelength), np.max(oned_wavelength))
