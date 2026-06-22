import time

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate, find_peaks

from despero.store.line import Line
from despero.utils import load_comp_standard

# script for testing

st = load_comp_standard()
comp = np.load("../../comp-old.npy", allow_pickle=True)


def slide(standard_order, step):
    max_index = len(standard_order.coordinates.columns) - step
    indexes = range(0, max_index)
    x = standard_order.coordinates.columns[:max_index]
    y = [standard_order.intensity[i + step] for i in indexes]
    return x, y


def get_delta(comp_order, st_x, st_y):
    deltas = []
    st_y = np.asarray(st_y)
    st_y -= np.min(st_y)
    comp_y = np.asarray(comp_order["intensity"])
    comp_y -= np.min(comp_y)
    for i in range(len(st_x)):
        delta = np.abs(comp_y[i] - st_y[i])
        deltas.append(delta / len(st_x))
    return np.sum(deltas)


def get_best_shift(comp_order, standard_order) -> list[float]:
    slide_steps = int(len(standard_order.coordinates.columns))
    deltas = []
    for step in range(slide_steps):
        print(f"slide step #{step+1}/{slide_steps}")
        st_x, st_y = slide(standard_order=standard_order, step=step)
        delta = get_delta(comp_order=comp_order, st_x=st_x, st_y=st_y)
        deltas.append(delta)
    best_shift = np.argmin(deltas)
    plt.plot(list(range(slide_steps)), deltas)
    plt.title(best_shift)
    plt.show()
    plt.cla()
    plt.clf()
    plt.plot(comp_order["columns"], comp_order["intensity"], color="black")
    plt.plot(standard_order.coordinates.columns - best_shift, standard_order.intensity, color="red")
    plt.title(f"best_shift = {best_shift}, delta = {deltas[best_shift]}")
    plt.show()
    plt.cla()
    plt.clf()
    return best_shift


# for i in range(len(comp)):
# start = time.time()
# get_best_shift(comp_order=comp[10], standard_order=st.orders[10])
# print(time.time() - start)

start = time.time()
st_peaks = []
for i_st in range(len(st.orders)):
    peaks, _ = find_peaks(st.orders[i_st].intensity, prominence=0.001)
    st_peaks.append(peaks)

comp_peaks = []
for i in range(len(comp)):
    peaks, _ = find_peaks(comp[i]["intensity"], prominence=0.001)
    comp_peaks.append(peaks)


def get_distances_between_peaks(peaks):
    distances = []
    for i in range(len(peaks)):
        d = []
        for j in range(len(peaks)):
            d.append(np.abs(peaks[i] - peaks[j]))
        distances.append(d)
    return distances


# c_d = get_distances_between_peaks(comp_peaks[10])
# s_d = get_distances_between_peaks(st_peaks[10])
# print(c_d)
# print(s_d)
# print(time.time() - start)

# TODO: add this to the standard
for i in range(len(st.orders)):
    # moves lines from .coordinates to .order
    st.orders[i].identified_lines = []
    for j, line in enumerate(st.orders[i].coordinates.lines):
        st.orders[i].identified_lines.append(Line(order=st.orders[i], column=line[0], wavelength=line[1]))

matches = []
for i in range(len(st.orders)):
    print(f"Matching #{i}...")
    _matches = []
    for j in range(len(st.orders)):
        _matches.append(st.orders[i].match_lines_from(st.orders[j]))
    matches.append(_matches)

for i, all_order_matches in enumerate(matches):
    n_matches = [len(matches_in_order) for matches_in_order in all_order_matches]
    ind = np.argmax(n_matches)
    print(f"#{i} <-> {ind}")
    # else:
    #     print(f"#{i} didn't match anything")

# TODO:
# 1. Revisit initial matches to assure linear growth and no repeating
# 2. Copy wavelength
# 3. Reformat the standard and export it
# 4. Test with new observations
# 5. Test with old observations
