import time

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate, find_peaks

from despero.parameters import CUTOFF
from despero.store.line import Line
from despero.utils import load_comp_standard

COMP_MATCHING_MAX_ADJACENT_ORDERS = 25
COMP_MATCHING_DISCARD_EDGE_N_ORDERS = 10
COMP_MATCHING_KEEP_STRONGEST_N_LINES_IN_COMP = 6

#############################################
#    DATA LOADING AND REFORMATTING
#############################################

start = time.monotonic()
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


comp = _reformat_comp(comp, st)
st = _reformat_standard(st)

#############################################
#    ACTUAL ALGORITHM
#############################################


def find_peaks_in_comp():
    for i in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len(comp.orders) - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
        peaks, _ = find_peaks(comp.orders[i].intensity, prominence=0.025, width=3)
        top_indexes = np.argsort(comp.orders[i].intensity[peaks])[-COMP_MATCHING_KEEP_STRONGEST_N_LINES_IN_COMP:]
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


# TODO: how do we properly cross-iterate over 2 arrays of different length?
def match(comp_st, comp_obs):
    matches = []
    for j in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len(comp_obs.orders) - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
        _matches = []
        for i in range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len(comp_st.orders) - COMP_MATCHING_DISCARD_EDGE_N_ORDERS):
            if i - COMP_MATCHING_MAX_ADJACENT_ORDERS < j < i + COMP_MATCHING_MAX_ADJACENT_ORDERS:
                _matches.append(comp_obs.orders[j].match_lines_from(comp_st.orders[i]))
            else:
                _matches.append([])
        matches.append(_matches)
        print(f"Matches for #{j}\t-\t{np.sum([len(m) for m in _matches])}")
    return matches


find_peaks_in_comp()
matches = match(st, comp)

comp_orders_in_st = []
print("RAW matches")
for i, all_order_matches in enumerate(matches):
    n_matches = [len(matches_in_order) for matches_in_order in all_order_matches]
    ind = np.argmax(n_matches)
    comp_orders_in_st.append(ind)
    print(f"#{i + COMP_MATCHING_DISCARD_EDGE_N_ORDERS} <-> {ind + COMP_MATCHING_DISCARD_EDGE_N_ORDERS}")

# # fit ax+b on comp_orders_in_st
# a, b = np.polyfit(range(COMP_MATCHING_DISCARD_EDGE_N_ORDERS, len(comp.orders) - COMP_MATCHING_DISCARD_EDGE_N_ORDERS), comp_orders_in_st, 1)
# comp_orders_in_st_fit = a*np.arange(0, len(comp.orders), 1, dtype=np.int16) + b + COMP_MATCHING_DISCARD_EDGE_N_ORDERS

# print("FIT matches")
# for i in range(len(comp_orders_in_st_fit)):
#     print(f"{i} <-> {comp_orders_in_st_fit[i]}")

# print(f"Took {time.monotonic() - start}s")
# plt.scatter(range(len(comp_orders_in_st_fit)), comp_orders_in_st_fit, color="red")
# plt.show()

# # за някои порядъци от стандарта може да получа 2 кандидата от компа
# # в такива случаи ще трябва да пусна нова проверка кой е правилният
# # ...
# # трябва да започна отначало този скрипт като внимавам на всяка стъпка
# # мисля че методите и класовете, които написах за тази задача, са ок
# # но не ги използвам правилно
# # със сигурност не фитирам правилно накрая
# # максималният брой отъждествени порядъци е равен на min(len(st.orders), len(comp.orders))
# # (не може да имаме 1 порядък от работния <-> 2 порядъка от стандарта или обратното)

l_s = len(st.orders)
l_c = len(comp.orders)

M = np.zeros((l_c + 1, l_s + 1))
for i_c in range(len(matches)):
    for i_s in range(len(matches[i_c])):
        M[i_c, i_s] = len(matches[i_c][i_s])


plt.figure(figsize=(10, 8))
plt.imshow(M, origin="lower", aspect="auto", interpolation="none")

plt.xlabel("Standard order")
plt.ylabel("Comparison order")
plt.title("Order matches")

# Grid at every cell
plt.xticks(np.arange(i_s + 1))
plt.yticks(np.arange(i_c + 1))

plt.grid(which="major", color="white", linewidth=0.5)

plt.tight_layout()
plt.show()


def best_monotonic_path(W):
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


path = best_monotonic_path(M)
print(path)
comp = np.array([p[0] for p in path])
std = np.array([p[1] for p in path])

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

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress

# (comp_order, standard_order)
pairs = [(i, v) for i, v in enumerate(comp_orders_in_st)]

# ------------------------------------------------------------
# Remove invalid matches
# ------------------------------------------------------------

pairs = [(c, s) for c, s in pairs if s > 0]

# sort by standard order
pairs.sort(key=lambda x: x[1])

standard_pairs = np.array([p[1] for p in pairs])
comp_pairs = np.array([p[0] for p in pairs])

# ------------------------------------------------------------
# Longest Increasing Subsequence on comp numbers
# ------------------------------------------------------------

n = len(comp_pairs)

length = [1] * n
parent = [-1] * n

for i in range(n):
    for j in range(i):
        if comp_pairs[j] < comp_pairs[i] and length[j] + 1 > length[i]:
            length[i] = length[j] + 1
            parent[i] = j

# reconstruct LIS
idx = np.argmax(length)
lis = []

while idx != -1:
    lis.append(idx)
    idx = parent[idx]

lis.reverse()

std_lis = standard_pairs[lis]
comp_lis = comp_pairs[lis]

# ------------------------------------------------------------
# Fit line
# ------------------------------------------------------------

fit = linregress(std_lis, comp_lis)

print(f"slope     = {fit.slope:.6f}")
print(f"intercept = {fit.intercept:.6f}")
print(f"R²        = {fit.rvalue**2:.8f}")

print("\nRecovered mapping:")
for s, c in zip(std_lis, comp_lis):
    print(f"{s:2d} -> {c:2d}")

import pdb

pdb.set_trace()

# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

plt.figure(figsize=(8, 5))

plt.scatter(standard_pairs, comp_pairs, c="lightgray", s=60, label="All matches")

plt.scatter(std_lis, comp_lis, c="red", s=60, label="LIS")

x = np.linspace(standard_pairs.min(), standard_pairs.max(), 100)
plt.plot(x, fit.slope * x + fit.intercept, linewidth=2, label="Linear fit")

plt.xlabel("Standard order")
plt.ylabel("Comparison order")
plt.legend()
plt.tight_layout()
plt.show()

for s, c in zip(std_lis, comp_lis):
    s = int(f"{s:2d}")
    c = int(f"{c:2d}")
    plt.clf()
    plt.cla()
    plt.plot(st.orders[s].coordinates.columns, st.orders[s].intensity, color="red", lw=2)
    plt.plot(comp.orders[c].coordinates.columns, comp.orders[c].intensity, color="black")
    plt.title(f"{s} <-> {c}")
    plt.show()
