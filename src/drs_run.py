from typing import Any

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
from src.utils import open_directory
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

    def start(self, ui: Any):
        if ui:
            ui.render_working_screen()

        store = Store(self.observation_dir)
        store.load_journal_from_file()

        if self.cosmic:
            ui.set_status(name="cosmics", finished=False)
            clean_cosmics(store)  # TODO: replace store with exposure
            ui.set_status(name="cosmics", finished=True)

        if self.bias:
            ui.set_status(name="bias", finished=False)
            store.create_master_biases()
            correct_for_bias(store)
            ui.set_status(name="bias", finished=True)

        if self.flat:
            ui.set_status(name="flat", finished=False)
            store.create_master_flats()
            ui.set_status(name="flat", finished=True)

        ui.set_status(name="orders", finished=False)
        find_orders_coordinates(store, use_master_flat=self.flat)
        ui.set_status(name="orders", finished=True)

        if self.flat:
            correct_for_flat(store)

        get_comp_for_stellar(store)

        ui.set_status(name="spectra", finished=False)
        extract_2d_spectra(store)  # TODO: replace store with exposure
        ui.set_status(name="spectra", finished=True)

        ui.set_status(name="wavelength", finished=False)
        calibrate_comp_spectra(store)  # TODO: replace store with exposure
        calibrate_stellar(store)  # TODO: replace store with exposure
        ui.set_status(name="wavelength", finished=True)

        if self.vhelio:
            correct_vhelio(store)  # TODO: replace store with exposure

        if self.fits_2d_norm or self.ascii_2d_norm or self.ascii_1d_norm:
            ui.set_status(name="normalize", finished=False)
            normalize(store)  # TODO: replace store with exposure
            ui.set_status(name="normalize", finished=True)
        if self.ascii_1d_norm:
            ui.set_status(name="stitch", finished=False)
            for observation in store.stellar:
                try:
                    stitch_oned(observation)
                except Exception as exc:
                    print(f"Error: cannot create 1D spectrum for {observation.fits_file}: {exc}")
            ui.set_status(name="stitch", finished=True)

        ui.set_status(name="save", finished=False)
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
        ui.set_status(name="save", finished=True)
        ui.root.after(0, ui.root.destroy)
        open_directory(store.output_directory)
        exit()
