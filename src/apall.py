from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

from src.parameters import (
    APERTURE_HEIGHT,
    CUTOFF,
    INTENSITY_THRESHOLD,
    NUMBER_OF_ECHELLE_ORDERS,
)
from src.store.order import Order
from src.store.order_coordinates import OrderCoordinates


def _get_orders_brightest_pixels(data: np.ndarray) -> list[list[int, int]]:
    vertical_profile = np.sum(data, axis=1)
    order_peaks_row, _ = find_peaks(vertical_profile, prominence=1)
    order_peaks_column = [np.argmax(data[row]) for row in order_peaks_row]
    all_peaks = [[order_peaks_row[i], order_peaks_column[i]] for i in range(len(order_peaks_row))]
    peaks_intensity = np.array([data[peak[0]][peak[1]] for peak in all_peaks])
    top_intensity_indexes = np.argsort(peaks_intensity)[::-1][:NUMBER_OF_ECHELLE_ORDERS]
    top_intensity_indexes.sort()
    # draw figure for paper
    if False:
        fig, ax = plt.subplots(nrows=2)
        ax[0].imshow(data.T, cmap="gray", interpolation="nearest", aspect="auto", vmin=0, vmax=500)
        # plt.imshow(data, cmap="gray")
        peaks_x = [order_peaks_column[i] for i in top_intensity_indexes]
        peaks_y = [order_peaks_row[i] for i in top_intensity_indexes]
        ax[0].scatter(peaks_y, peaks_x, color="red")
        ax[1].plot(np.linspace(0, data.shape[0], data.shape[0]), vertical_profile)
        plt.show()
        # plt.savefig("order_peaks-tung-led.png")
    return [[order_peaks_row[i], order_peaks_column[i]] for i in top_intensity_indexes]


def _get_brightest_neighbouring_pixel_in_order(image: np.ndarray, row: int, column: int, direction: str) -> dict | None:
    if direction == "left":
        column_shift = -1
    elif direction == "right":
        column_shift = 1
    all_neighbours = [
        {
            "row": row + row_shift,
            "column": column + column_shift,
            "intensity": image[row + row_shift][column + column_shift],
        }
        for row_shift in range(-1, 2)
        if row + row_shift >= 0
        and row + row_shift < image.shape[0]
        and column + column_shift >= 0
        and column + column_shift < image.shape[1]
    ]
    all_neighbours.sort(key=lambda x: x["intensity"])
    if len(all_neighbours) > 0:
        return all_neighbours[-1]


def _trace_direction(
    image: np.ndarray, starting_row: int, starting_column: int, direction: str, pixels: list[dict]
) -> list[dict]:
    row, column = starting_row, starting_column
    while column >= CUTOFF if direction == "left" else column <= image.shape[1] - 1 - CUTOFF:
        pixel = _get_brightest_neighbouring_pixel_in_order(image, row, column, direction)
        if pixel is None:
            # signal lost
            break
        if pixel["intensity"] < INTENSITY_THRESHOLD and len(pixels) < 10:
            # tracing a cosmic
            return []
        pixels.append(pixel)
        column, row = pixel["column"], pixel["row"]
    return pixels


def _trace_order(image: np.ndarray, starting_row: int, starting_column: int, found: bool) -> list[dict]:
    pixels = [
        {
            "row": starting_row,
            "column": starting_column,
            "intensity": image[starting_row][starting_column],
        }
    ]
    if pixels[0]["intensity"] < INTENSITY_THRESHOLD:
        return []

    pixels = _trace_direction(image, starting_row, starting_column, "left", [])
    pixels = _trace_direction(image, starting_row, starting_column, "right", pixels)
    pixels.sort(key=lambda x: x["column"])

    # check if order overlaps an already found one
    already_found_pixels = []
    for f in found:
        already_found_pixels += f.tolist()
    for n, pixel in enumerate(pixels):
        if n % 100 == 0:
            if [pixel["column"], pixel["row"]] in already_found_pixels:
                return []
    return pixels


def find_orders_coordinates(store: Any, use_master_flat: bool, degree: int = 10, draw: bool = False) -> None:
    if use_master_flat:
        data = store.master_flats[0].raw_data
    else:
        data = np.median([flat.raw_data for flat in store.flat], axis=0)
    orders_brightest_pixels = _get_orders_brightest_pixels(data)
    found = []
    for i in range(len(orders_brightest_pixels)):
        starting_row = orders_brightest_pixels[i][0]
        starting_column = orders_brightest_pixels[i][1]
        order = _trace_order(data, starting_row, starting_column, found)
        if order:
            found.append(np.asarray([[point["column"], point["row"]] for point in order]))
    order_coeffs = [np.polyfit(order[:, 0], order[:, 1], degree) for order in found]
    columns = np.linspace(CUTOFF, data.shape[1] - 1 - CUTOFF, data.shape[1] - 2 * CUTOFF, dtype=int)
    found = [{"columns": columns, "rows": np.rint(np.polyval(coeffs, columns)).astype(int)} for coeffs in order_coeffs]

    if draw:
        plt.rcParams.update({"font.size": 24})
        plt.imshow(data, cmap="gray", vmin=500, vmax=10000)

    for i in range(len(found)):
        coordinates = OrderCoordinates(i, found[i]["rows"], found[i]["columns"])
        store.order_coordinates.append(coordinates)
        if draw:
            plt.plot(coordinates.columns, coordinates.rows, color="red", alpha=0.35)
    if draw:
        title = f"Echelle orders found: {len(found)}"
        plt.title(title)
        plt.xlabel("Column number (X)")
        plt.ylabel("Row number (Y)")
        plt.show()


def _extract_2d(store: Any, observation: Any) -> None:
    if observation.wavelength_calibrated:
        return

    for coordinates in store.order_coordinates:
        order = Order(observation, coordinates)
        for i in range(len(coordinates.rows)):
            row = int(coordinates.rows[i])
            column = int(coordinates.columns[i])

            intensity_aggregate = [observation.raw_data[row][column]]
            for j in range(1, APERTURE_HEIGHT):
                if row + j < observation.raw_data.shape[0]:
                    intensity_aggregate.append(observation.raw_data[row + j][column])
                if row - j >= 0:
                    intensity_aggregate.append(observation.raw_data[row - j][column])
            order.intensity.append(np.average(intensity_aggregate))
        observation.orders.append(order)
    observation.wavelength_calibrated = True


def extract_2d_spectra(observation: Any) -> None:
    store = observation.store
    _extract_2d(store, observation)
    _extract_2d(store, store.comp[observation.comp_index])
