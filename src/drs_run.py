from pyraf import iraf
from src.apall import extract_2d_spectra, find_orders_coordinates
from src.calibrate import (
    calibrate_comp_spectra,
    calibrate_stellar,
    get_comp_for_stellar,
)
from src.initial_corrections import (
    clean_cosmics,
    correct_for_bias,
    correct_for_flat,
    correct_for_vhelio,
)
from src.normalize import normalize, stitch_oned
from src.save.as_ascii import save_as_ascii
from src.save.as_fits import save_as_fits
from src.store.store import Store
from src.utils import add_vhelio_to_fits


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

        if self.vhelio:
            iraf.noao()
            iraf.rv()

        if self.cosmic:
            clean_cosmics(store)

        if self.vhelio:
            add_vhelio_to_fits(store)

        if self.bias:
            # fix bias correction
            store.create_master_biases()
            correct_for_bias(store)

        if self.flat:
            store.create_master_flats()
            find_orders_coordinates(store, use_master_flat=True)
            correct_for_flat(store)
        else:
            find_orders_coordinates(store, use_master_flat=False)

        get_comp_for_stellar(store)
        extract_2d_spectra(store)
        calibrate_comp_spectra(store)
        calibrate_stellar(store)

        if self.vhelio:
            correct_for_vhelio(store)

        # save_fits(store)
        normalize(store)
        # stitch_oned(store)
        # save_ascii(store)

        for observation in store.stellar:
            # save_as_fits(observation)
            save_as_ascii(observation)
