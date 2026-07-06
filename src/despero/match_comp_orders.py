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

    M = np.full((len_comp, len_st), -np.inf)
    for j in range(len_comp):
        for i in range(len_st):
            if abs(i - j) > COMP_MATCHING_MAX_ADJACENT_ORDERS:
                continue

            matches = comp.orders[j].match_lines_from(standard.orders[i])
            M[j, i] = len(matches)

    return M


def _get_best_monotonic_path(W):
    discard = COMP_MATCHING_DISCARD_EDGE_N_ORDERS

    n_comp, n_std = W.shape

    dp = np.full((n_comp, n_std), -np.inf)
    prev = np.full((n_comp, n_std), -1, dtype=int)

    dp[discard] = W[discard]

    for i in range(discard + 1, n_comp - discard):
        for j in range(discard, n_std - discard):
            best_score = -np.inf
            best_prev = -1

            for k in range(discard, j):
                if not np.isfinite(dp[i - 1, k]):
                    continue

                score = dp[i - 1, k] + W[i, j]
                if score > best_score:
                    best_score = score
                    best_prev = k

            dp[i, j] = best_score
            prev[i, j] = best_prev

    last_row = n_comp - discard - 1

    j = np.argmax(dp[last_row])

    path = []

    i = last_row
    while i >= discard and j >= 0:
        path.append((i, j))
        j = prev[i, j]
        i -= 1

    path.reverse()

    return path


def get_comp_and_standard_matching_orders(comp, standard, plot=False):
    _add_most_likely_lines_to_comp(comp)
    M = _get_match_matrix(standard, comp)
    print(M.shape)
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
        print(path)
        plt.show()
    return path
