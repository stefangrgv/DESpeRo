from src.apall import extract_2d_spectra, find_orders_coordinates
from src.calibrate import (
    calibrate_comp_spectra,
    calibrate_stellar,
    get_comp_for_stellar,
)
from src.initial_corrections import clean_cosmics, correct_for_bias, correct_for_flat
from src.normalize import normalize, stitch_oned
from src.save.as_ascii import save_as_1d_ascii, save_as_2d_ascii
from src.save.as_fits import save_as_fits
from src.store.store import Store
from src.vhelio import correct_vhelio


class DRSRun:
    def __init__(self, observation_dir: str, cosmic: bool, bias: bool, flat: bool, vhelio: bool):
        self.observation_dir = observation_dir
        self.cosmic = cosmic
        self.bias = bias
        self.flat = flat
        self.vhelio = vhelio

    def start(self):
        store = Store(self.observation_dir)
        store.load_journal_from_file()

        if self.cosmic:
            clean_cosmics(store)

        if self.bias:
            # fix bias correction
            store.create_master_biases()
            correct_for_bias(store)

        if self.flat:
            store.create_master_flats()
            find_orders_coordinates(store, use_master_flat=True, draw=True)
            correct_for_flat(store)
        else:
            find_orders_coordinates(store, use_master_flat=False, draw=True)

        get_comp_for_stellar(store)
        extract_2d_spectra(store)
        calibrate_comp_spectra(store)
        calibrate_stellar(store)

        if self.vhelio:
            correct_vhelio(store)

        normalize(store)
        stitch_oned(store)

        for observation in store.stellar:
            save_as_2d_ascii(observation)
            save_as_1d_ascii(observation)
            save_as_fits(observation)
            save_as_fits(observation, normalized=True)
        exit()
