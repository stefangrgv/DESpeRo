import tkinter as tk
from tkinter import ttk
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.signal import find_peaks

from src.parameters import APERTURE_HEIGHT, CUTOFF, INTENSITY_THRESHOLD, NUMBER_OF_ECHELLE_ORDERS
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
    image: np.ndarray,
    starting_row: int,
    starting_column: int,
    direction: str,
    pixels: list[dict],
    threshold: int,
) -> list[dict]:
    row, column = starting_row, starting_column
    while column >= CUTOFF if direction == "left" else column <= image.shape[1] - 1 - CUTOFF:
        pixel = _get_brightest_neighbouring_pixel_in_order(image, row, column, direction)
        if pixel is None:
            # signal lost
            break
        if pixel["intensity"] < threshold and len(pixels) < 10:
            # tracing a cosmic
            return []
        pixels.append(pixel)
        column, row = pixel["column"], pixel["row"]
    return pixels


def _trace_order(image: np.ndarray, starting_row: int, starting_column: int, found: bool, threshold: int) -> list[dict]:
    pixels = [
        {
            "row": starting_row,
            "column": starting_column,
            "intensity": image[starting_row][starting_column],
        }
    ]
    if pixels[0]["intensity"] < threshold:
        return []

    pixels = _trace_direction(image, starting_row, starting_column, "left", [], threshold)
    pixels = _trace_direction(image, starting_row, starting_column, "right", pixels, threshold)
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


def _get_coordinates(data: Any, degree: int, threshold: int = INTENSITY_THRESHOLD):
    orders_brightest_pixels = _get_orders_brightest_pixels(data)
    found = []
    for i in range(len(orders_brightest_pixels)):
        starting_row = orders_brightest_pixels[i][0]
        starting_column = orders_brightest_pixels[i][1]
        order = _trace_order(data, starting_row, starting_column, found, threshold)
        if order:
            found.append(np.asarray([[point["column"], point["row"]] for point in order]))
    order_coeffs = [np.polyfit(order[:, 0], order[:, 1], degree) for order in found]
    columns = np.linspace(CUTOFF, data.shape[1] - 1 - CUTOFF, data.shape[1] - 2 * CUTOFF, dtype=int)
    found = [{"columns": columns, "rows": np.rint(np.polyval(coeffs, columns)).astype(int)} for coeffs in order_coeffs]
    return found


def _apply_found(store: Any, found: list, draw: bool, ax: Any, data: list) -> None:
    store.order_coordinates = []
    if draw:
        ax.cla()
        img = ax.imshow(data, cmap="gray", vmin=0, vmax=200)

    for i in range(len(found)):
        coordinates = OrderCoordinates(i, found[i]["rows"], found[i]["columns"])
        store.order_coordinates.append(coordinates)
        if draw:
            ax.scatter(found[i]["columns"], found[i]["rows"], color="red", s=1, alpha=0.15)

    if draw:
        return img


def _draw_standard_orders(comp_standard, ax):
    for order_std in comp_standard.orders:
        ax.scatter(order_std.coordinates.columns, order_std.coordinates.rows, color="lime", s=2, alpha=0.15)


def find_orders_coordinates(
    store: Any, use_master_flat: bool, comp_standard: Any, degree: int = 10, draw: bool = False
) -> None:
    if use_master_flat:
        data = store.master_flats[0].raw_data
    else:
        data = np.median([flat.raw_data for flat in store.flat], axis=0)

    found = _get_coordinates(data, degree)

    if draw:
        fig = plt.gcf()
        ax = plt.gca()
        root = tk.Tk()
        root.title("Order coordinates")

    img = _apply_found(store, found, draw, ax, data)

    if draw:
        _draw_standard_orders(comp_standard, ax)

        frame_plot = ttk.Frame(root)
        frame_plot.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas = FigureCanvasTkAgg(fig, master=frame_plot)
        canvas.draw()

        # Get the widget from the canvas and pack it into the window
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # Add the navigation toolbar
        toolbar = NavigationToolbar2Tk(canvas, frame_plot)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # --- Controls Frame ---
        frame_controls = ttk.Frame(root)
        frame_controls.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        # Entry for vmin
        ttk.Label(frame_controls, text="vmin:").pack(side=tk.LEFT)
        entry_vmin = ttk.Entry(frame_controls, width=6)
        entry_vmin.insert(0, "0")
        entry_vmin.pack(side=tk.LEFT)

        # Entry for vmax
        ttk.Label(frame_controls, text="vmax:").pack(side=tk.LEFT)
        entry_vmax = ttk.Entry(frame_controls, width=6)
        entry_vmax.insert(0, "100")
        entry_vmax.pack(side=tk.LEFT)

        # Update button
        def update_color_scale():
            try:
                vmin = float(entry_vmin.get())
                vmax = float(entry_vmax.get())
                img.set_clim(vmin, vmax)  # Update color limits
                canvas.draw()
            except ValueError:
                print("Please enter valid numbers for vmin and vmax.")

        ttk.Button(frame_controls, text="Update Color Scale", command=update_color_scale).pack(side=tk.LEFT, padx=10)

        ttk.Label(frame_controls, text="vmax:").pack(side=tk.LEFT)
        entry_threshold = ttk.Entry(frame_controls, width=6)
        entry_threshold.insert(0, str(INTENSITY_THRESHOLD))
        entry_threshold.pack(side=tk.LEFT)

        def update_threshold():
            try:
                threshold = float(entry_threshold.get())
                found = _get_coordinates(data, degree, threshold)
                img = _apply_found(store, found, draw, ax, data)
                _draw_standard_orders(comp_standard, ax)
                canvas.draw()
            except ValueError:
                print("Please enter a valid integer.")

        ttk.Button(frame_controls, text="Update intensity threshold", command=update_threshold).pack(
            side=tk.LEFT, padx=10
        )
        root.mainloop()


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
