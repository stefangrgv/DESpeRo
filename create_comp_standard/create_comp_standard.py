import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from lines import lines
from save import save_comp_as_npy
from scipy.signal import find_peaks

from pyraf import iraf
from src.apall import extract_2d_spectra, find_orders_coordinates
from src.calibrate import fit_chebyshev
from src.fit import find_line_peak, gaussian
from src.initial_corrections import correct_for_bias, correct_for_flat
from src.store.store import Store

LIVE_PLOT = True
USE_GAUSSIAN_FIT = False
SUGGEST_PEAKS = False
SHOW_APERTURES = True

correct_bias = False
correct_flat = False

matplotlib.use("TkAgg")


def plot_comp_standard(lines):
    comp_standard = np.load("../comp_standard.npy", allow_pickle=True).tolist()
    for order in comp_standard.orders:
        number = order.order_coordinates.number
        if number < 14:
            continue
        title = f"Order #{number}"
        if SUGGEST_PEAKS:
            order_peaks_column, _ = find_peaks(order.intensity, prominence=0.1)
            inc_y_shift_peaks = np.max(order.intensity) / len(order_peaks_column)
        inc_y_shift = np.max(order.intensity) / 10
        if lines.get(number, None) is not None and len(lines[number]):
            # plt.rcParams.update({"font.size": 24})
            # if LIVE_PLOT:
            inc_y_shift = np.max(order.intensity) / (len(lines[number]) + 1)
            _, ax = plt.subplots(nrows=2, sharex=True)
            ax[1].set_ylabel(r"Wavelength (${\AA}$)")
            ax[1].set_xlabel("Column number")
            ax[0].set_ylabel("Normalized intensity")
            cheby_fit = fit_chebyshev(lines.get(number), degree=3)
            order.wavelength = cheby_fit(order.order_coordinates.columns)
            ax[0].set_title(title)
            ax[1].plot(order.order_coordinates.columns, order.wavelength, color="green")
            ax[0].plot(order.order_coordinates.columns, order.intensity, color="black")
            if SUGGEST_PEAKS:
                for i, col in enumerate(order_peaks_column):
                    ax[1].axvline(col, color="green", ls="--", lw=2)
                    ax[1].text(x=col, y=(i + 1) * inc_y_shift, s=f"{col}", color="green")
            for i, point in enumerate(lines[number]):
                ax[1].scatter(point[0], point[1], color="black", s=50)
                ax[0].axvline(point[0], color="red", ls="--", lw=2)
                ax[0].text(x=point[0], y=(i + 1) * 1.5 * inc_y_shift, s=f"{point[1]}", color="black")
            plt.show()


def create_comp_standard():
    directory = input("Enter path to observations directory: ")
    store = Store(directory)
    store.load_journal_from_file()

    if correct_bias or correct_flat:
        iraf.noao()
        iraf.rv()
        iraf.imred()
        iraf.ccd()

    if correct_bias:
        # do more tests to make sure bias correction works as intended
        store.create_master_biases()
        correct_for_bias(store)

    if correct_flat:
        store.create_master_flats()
        find_orders_coordinates(store, use_master_flat=True, draw=SHOW_APERTURES)
        correct_for_flat(store)
    else:
        find_orders_coordinates(store, use_master_flat=False, draw=SHOW_APERTURES)
    extract_2d_spectra(store, store.comp)

    comp_standard = store.comp[0]
    for i, order in enumerate(comp_standard.orders):
        comp_standard.orders[i].intensity = np.asarray(comp_standard.orders[i].intensity, dtype=np.float16)
        comp_standard.orders[i].intensity /= np.max(comp_standard.orders[i].intensity)
        points_in_order = lines.get(i, None)
        if points_in_order is not None:
            comp_standard.orders[i].order_coordinates.lines = points_in_order
            fit_points = []
            for point in points_in_order:
                # plot the gaussians on the spectrum to see if they're good
                if USE_GAUSSIAN_FIT:
                    try:
                        gaussian_fit_parameters = find_line_peak(
                            order.order_coordinates.columns,
                            order.intensity,
                            point[0],
                        )
                        if LIVE_PLOT:
                            gauss_fit = gaussian(
                                order.order_coordinates.columns,
                                gaussian_fit_parameters["a"],
                                gaussian_fit_parameters["x0"],
                                gaussian_fit_parameters["sigma"],
                                gaussian_fit_parameters["offset"],
                            )
                            plt.plot(
                                order.order_coordinates.columns,
                                gauss_fit,
                                color="red",
                                alpha=0.5,
                            )
                        fit_points.append((gaussian_fit_parameters["x0"], point[1]))
                    except RuntimeError as e:
                        print(e)
                        fit_points.append((point[0], point[1]))
                else:
                    fit_points.append((point[0], point[1]))
            if LIVE_PLOT:
                plt.show()
            comp_standard.orders[i].order_coordinates.lines = fit_points

    return comp_standard


if __name__ == "__main__":
    comp_standard = create_comp_standard()
    np.save("../comp_standard.npy", comp_standard, allow_pickle=True)
    plot_comp_standard(lines)
