import time

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate, find_peaks

from despero.parameters import CUTOFF
from despero.store.line import Line
from despero.utils import load_comp_standard

MAX_ADJACENT_ORDERS = 25
DISCARD_EDGE_N_ORDERS = 10
KEEP_TOP_N_PEAKS_IN_COMP = 6

st = load_comp_standard()
comp = np.load("../../comp-old.npy", allow_pickle=True)

def _reformat_comp(old_comp, standard):
    from despero.store.observation import Observation
    from despero.store.order import Order
    from despero.store.order_coordinates import OrderCoordinates
    from despero.utils import EXPOSURE_TYPES

    new_comp = Observation(
        store=standard.store, fits_file=None, exposure_type=EXPOSURE_TYPES.COMP, date=None, exposure_time=0, load=False
    )
    new_comp.orders = []
    for i, order in enumerate(old_comp):
        coordinates = OrderCoordinates(i, [], order["columns"])
        new_comp.orders.append(Order(observation=new_comp, coordinates=coordinates))
        new_comp.orders[-1].intensity = order["intensity"]
    return new_comp


def _reformat_standard(st):
    # TODO: add this to the standard
    for i in range(len(st.orders)):
        # moves lines from .coordinates to .order
        st.orders[i].identified_lines = []
        for line in st.orders[i].coordinates.lines:
            st.orders[i].identified_lines.append(Line(order=st.orders[i], column=line[0], wavelength=line[1]))
    return st

#############################################
#    ACTUAL ALGORITHM
#############################################


def find_peaks_in_comp(comp):
    for i in range(DISCARD_EDGE_N_ORDERS, len(comp.orders) - DISCARD_EDGE_N_ORDERS):
        peaks, _ = find_peaks(comp.orders[i].intensity, prominence=0.025, width=3)
        top_indexes = np.argsort(comp.orders[i].intensity[peaks])[-KEEP_TOP_N_PEAKS_IN_COMP:]
        peaks = peaks[top_indexes]
        # plt.plot(comp.orders[i].coordinates.columns, comp.orders[i].intensity, color="black")
        # plt.plot(st.orders[i].coordinates.columns, st.orders[i].intensity, color="green")
        for peak in peaks:
            # plt.axvline(peak + CUTOFF, color="red", ls='--')
            comp.orders[i].identified_lines.append(Line(order=comp.orders[i], column=peak + CUTOFF))
        # plt.title(i)
        # plt.show()
        # plt.cla()
        # plt.clf()

def get_match_matrix(comp_st, comp_obs):
    len_st = len(st.orders)
    len_comp = len(comp.orders)

    matches = []
    for j in range(DISCARD_EDGE_N_ORDERS, len_comp - DISCARD_EDGE_N_ORDERS):
        _matches = []
        for i in range(DISCARD_EDGE_N_ORDERS, len_st - DISCARD_EDGE_N_ORDERS):
            if i - MAX_ADJACENT_ORDERS < j < i + MAX_ADJACENT_ORDERS:
                _matches.append(comp_obs.orders[j].match_lines_from(comp_st.orders[i]))
            else:
                _matches.append([])
        matches.append(_matches)

    M = np.zeros((len_comp + 1, len_st + 1))
    for i_c in range(len(matches)):
        for i_s in range(len(matches[i_c])):
            M[i_c, i_s] = len(matches[i_c][i_s])

    return M

def get_best_monotonic_path(W):
    n_comp, n_std = W.shape

    dp = np.full((n_comp, n_std), -np.inf)
    prev = np.full((n_comp, n_std), -1, dtype=int)

    # first row
    dp[0] = W[0]

    for i in range(1, n_comp):
        for j in range(n_std):
            if j == 0:
                continue

            k = np.argmax(dp[i - 1, :j])
            dp[i, j] = dp[i - 1, k] + W[i, j]
            prev[i, j] = k

    # traceback
    j = np.argmax(dp[-1])

    path = []

    for i in reversed(range(n_comp)):
        path.append((i, j))
        j = prev[i, j]

    path.reverse()

    return path


comp = _reformat_comp(comp, st)
st = _reformat_standard(st)

def get_comp_and_st_matching_pairs(comp, st):
    find_peaks_in_comp(comp)
    M = get_match_matrix(st, comp)
    return get_best_monotonic_path(M)
