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
    discard = COMP_MATCHING_DISCARD_EDGE_N_ORDERS # keep it short
    M = W[discard:-discard,:]
    n_comp, n_std = M.shape

    dp = np.full((n_comp, n_std), -np.inf)
    prev = np.full((n_comp, n_std), -1, dtype=int)
    dp[0] = M[0]

    for i in range(1, n_comp):
        for j in range(1, n_std):
            k = np.argmax(dp[i - 1, :j])
            dp[i, j] = dp[i - 1, k] + M[i, j]
            prev[i, j] = k

    j = np.argmax(dp[-1])
    path = []
    for i in reversed(range(n_comp)):
        path.append((i + discard, j))
        j = prev[i, j]
    path.reverse()

    extended_path = []
    delta = np.median([p[0] - p[1] for p in path]).astype(int)
    path_1st_comp, path_1st_std = path[0]
    for comp_order_n in range(path_1st_comp):
        std_order_n = comp_order_n - delta
        if comp_order_n > 0 and std_order_n > 0:
            extended_path.append((comp_order_n, std_order_n))
    extended_path = [*extended_path, *path]
    path_last_comp, _ = path[-1]
    absolute_last_comp_order_n = W.shape[0]
    absolute_last_std_order_n = W.shape[1]
    for comp_order_n in range(path_last_comp, absolute_last_comp_order_n):
        std_order_n = comp_order_n - delta
        if std_order_n <= absolute_last_std_order_n:
            extended_path.append((comp_order_n, std_order_n))

    return extended_path


def get_comp_and_standard_matching_orders(comp, standard, plot=True):
    _add_most_likely_lines_to_comp(comp)
    M = _get_match_matrix(standard, comp)
    path = _get_best_monotonic_path(M)
    comp = np.array([p[0] for p in path])
    std = np.array([p[1] for p in path])

    if plot:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(M, origin="lower", cmap="viridis", aspect="auto", interpolation="nearest")

        # Optimal path
        ax.plot(std, comp, "r-", lw=2, label="DP path")
        ax.scatter(std, comp, c="red", s=25)

        ax.set_xlabel("Standard order")
        ax.set_ylabel("Comparison order")

        plt.colorbar(im, ax=ax, label="Score")
        ax.legend()

        plt.tight_layout()
        plt.show()
    return path
