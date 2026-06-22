import time

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate, find_peaks

from despero.store.line import Line
from despero.utils import load_comp_standard
from despero.parameters import CUTOFF

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



def get_distances_between_peaks(peaks):
    distances = []
    for i in range(len(peaks)):
        d = []
        for j in range(len(peaks)):
            d.append(np.abs(peaks[i] - peaks[j]))
        distances.append(d)
    return distances

def _reformat_comp(old_comp, standard):
    from despero.store.observation import Observation
    from despero.store.order import Order
    from despero.store.order_coordinates import OrderCoordinates
    from despero.utils import EXPOSURE_TYPES
    new_comp = Observation(store=standard.store, fits_file=None, exposure_type=EXPOSURE_TYPES.COMP, date=None, exposure_time=0, load=False)
    new_comp.orders = []
    for i, order in enumerate(old_comp):
        coordinates = OrderCoordinates(i, [], order["columns"])
        new_comp.orders.append(Order(observation=new_comp, coordinates=coordinates))
        new_comp.orders[-1].intensity = order["intensity"]
    return new_comp

comp = _reformat_comp(comp, st)

# TODO: add this to the standard
for i in range(len(st.orders)):
    # moves lines from .coordinates to .order
    st.orders[i].identified_lines = []
    for line in st.orders[i].coordinates.lines:
        st.orders[i].identified_lines.append(Line(order=st.orders[i], column=line[0], wavelength=line[1]))

# TODO: I have way too many matches, something isn't right
for i in range(1, len(comp.orders)):
    peaks, _ = find_peaks(comp.orders[i].intensity, prominence=0.025, width=3)
    print(i, len(peaks))
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
    for i in range(len(comp_st.orders)):
        _matches = []
        for j in range(len(comp_obs.orders)):
            if i - 3 < j < i + 3:
                _matches.append(comp_st.orders[i].match_lines_from(comp_obs.orders[j]))
            else:
                _matches.append([])
        matches.append(_matches)
        print(f"Matches for #{i}\t-\t{np.sum([len(m) for m in _matches])}")
    return matches

matches = match(st, comp)

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
