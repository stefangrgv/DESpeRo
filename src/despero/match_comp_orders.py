import numpy as np
from scipy.signal import find_peaks

from despero.parameters import (COMP_MATCHING_DISCARD_EDGE_N_ORDERS,
                                COMP_MATCHING_KEEP_STRONGEST_N_LINES_IN_COMP,
                                COMP_MATCHING_MAX_ADJACENT_ORDERS, CUTOFF)
from despero.store.line import Line


def _add_most_likely_lines_to_comp(comp):
    for i in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len(comp.orders) - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
        peaks, _ = find_peaks(comp.orders[i].intensity, prominence=0.025, width=3)
        top_indexes = np.argsort(comp.orders[i].intensity[peaks])[-COMP_MATCHING_KEEP_STRONGEST_N_LINES_IN_COMP:]
        peaks = peaks[top_indexes]
        for peak in peaks:
            comp.orders[i].identified_lines.append(Line(order=comp.orders[i], column=peak + CUTOFF))


def _get_match_matrix(standard, comp):
    len_st = len(standard.orders)
    len_comp = len(comp.orders)

    matches = []
    for j in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len_comp - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
        _matches = []
        for i in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len_st - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
            if i - COMP_MATCHING_MAX_ADJACENT_ORDERS < j < i + COMP_MATCHING_MAX_ADJACENT_ORDERS:
                _matches.append(comp.orders[j].match_lines_from(standard.orders[i]))
            else:
                _matches.append([])
        matches.append(_matches)

    M = np.zeros((len_comp + 1, len_st + 1))
    for i_c in range(len(matches)):
        for i_s in range(len(matches[i_c])):
            M[i_c, i_s] = len(matches[i_c][i_s])

    return M


def _get_best_monotonic_path(W):
    n_comp, n_std = W.shape

    dp = np.full((n_comp, n_std), -np.inf)
    dp[0] = W[0]
    prev = np.full((n_comp, n_std), -1, dtype=int)

    for i in range(1, n_comp):
        for j in range(n_std):
            if j == 0:
                continue

            k = np.argmax(dp[i - 1, :j])
            dp[i, j] = dp[i - 1, k] + W[i, j]
            prev[i, j] = k

    j = np.argmax(dp[-1])
    path = []
    for i in reversed(range(n_comp)):
        path.append((i, j))
        j = prev[i, j]
    path.reverse()

    return path


def get_comp_and_standard_matching_orders(comp, standard):
    _add_most_likely_lines_to_comp(comp)
    M = _get_match_matrix(standard, comp)
    return _get_best_monotonic_path(M)
