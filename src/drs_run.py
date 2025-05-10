from src.apall import extract_2d_spectra, find_orders_coordinates
from src.calibrate import (
    calibrate_comp_spectra,
    calibrate_stellar,
    get_comp_for_stellar,
)
from src.initial_corrections import clean_cosmics, correct_for_bias, correct_for_flat
from src.normalize import normalize, stitch_oned
from src.save.as_ascii import save_as_1d_ascii_norm, save_as_2d_ascii
from src.save.as_fits import save_as_fits
from src.store.store import Store
from src.vhelio import correct_vhelio


class DRS_Run:
    def __init__(
        self,
        observation_dir: str,
        cosmic: bool,
        bias: bool,
        flat: bool,
        vhelio: bool,
        fits_2d: bool,
        fits_2d_norm: bool,
        ascii_2d: bool,
        ascii_2d_norm: bool,
        ascii_1d_norm: bool,
    ):
        self.observation_dir = observation_dir
        self.cosmic = cosmic
        self.bias = bias
        self.flat = flat
        self.vhelio = vhelio
        self.fits_2d = fits_2d
        self.fits_2d_norm = fits_2d_norm
        self.ascii_2d = ascii_2d
        self.ascii_2d_norm = ascii_2d_norm
        self.ascii_1d_norm = ascii_1d_norm

    def start(self):
        store = Store(self.observation_dir)
        store.load_journal_from_file()

        if self.cosmic:
            clean_cosmics(store)

        if self.bias:
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
            correct_vhelio(store)

        normalize(store)
        stitch_oned(store)

        for observation in store.stellar:
            if self.fits_2d:
                save_as_fits(observation)
            if self.fits_2d_norm:
                save_as_fits(observation, normalized=True)
            if self.ascii_2d:
                save_as_2d_ascii(observation)
            if self.ascii_2d_norm:
                save_as_2d_ascii(observation, normalized=True)
            if self.ascii_1d_norm:
                save_as_1d_ascii_norm(observation)
        exit()
