from typing import Any

from despero.apall import extract_2d_spectra, find_orders_coordinates
from despero.calibrate import (calibrate_comp_spectra, calibrate_stellar,
                               get_comp_for_stellar, get_useful_comp_indexes)
from despero.initial_corrections import correct_for_flat
from despero.normalize import normalize, stitch_oned
from despero.save.as_ascii import save_as_1d_ascii_norm, save_as_2d_ascii
from despero.save.as_fits import save_as_fits
from despero.store.store import Store
from despero.utils import load_comp_standard, open_directory


class Quicklook:
    def __init__(
        self,
        observation_dir: str,
        cosmic: bool,
        flat: bool,
        fits_2d: bool,
        fits_2d_norm: bool,
        ascii_2d: bool,
        ascii_2d_norm: bool,
        ascii_1d_norm: bool,
    ):
        self.observation_dir = observation_dir
        self.cosmic = cosmic
        self.flat = flat
        self.fits_2d = fits_2d
        self.fits_2d_norm = fits_2d_norm
        self.ascii_2d = ascii_2d
        self.ascii_2d_norm = ascii_2d_norm
        self.ascii_1d_norm = ascii_1d_norm

    def start(self, reporter: Any | None = None, show_files_when_done: bool = False):
        # TODO: handle possibly missing dimension

        if reporter:
            reporter.render_working_screen()

        store = Store(self.observation_dir)
        store.load_journal_from_file()

        if self.flat:
            if reporter:
                reporter.set_status(name="flat", finished=False)

            store.create_master_flats()
            if reporter:
                reporter.set_master_flats(store.master_flats)

            if reporter:
                reporter.set_status(name="flat", finished=True)

        if reporter:
            reporter.set_status(name="orders", finished=False)
        find_orders_coordinates(store, use_master_flat=self.flat)

        if reporter:
            reporter.set_status(name="orders", finished=True)
            reporter.set_order_coordinates(store.order_coordinates)

        if self.flat:
            for master_flat in store.master_flats:
                for observation in [observation for observation in store.stellar]:
                    try:
                        correct_for_flat(observation, master_flat)
                    except Exception as exc:
                        print(f"Error: cannot apply flat correction to {observation.fits_file}: {exc}")
        get_comp_for_stellar(store)

        if reporter:
            reporter.set_status(name="spectra", finished=False)

        for observation in store.stellar:
            try:
                extract_2d_spectra(observation)
            except Exception as exc:
                print(f"Error: cannot extract 2D spectrum from {observation.fits_file}: {exc}")

        if reporter:
            reporter.set_status(name="spectra", finished=True)
            reporter.set_status(name="wavelength", finished=False)

        try:
            comp_standard = load_comp_standard()
        except FileNotFoundError as err:
            print("Error: comp standard not found!")
            print(err)
            return

        if reporter:
            reporter.set_comp_standard(comp_standard)

        useful_comp_indexes = get_useful_comp_indexes(store)
        for comp_index, comp in enumerate(store.comp):
            if comp_index not in useful_comp_indexes:
                continue
            calibrate_comp_spectra(comp, comp_standard)

        if reporter:
            reporter.set_comp(store.comp)
            reporter.set_status(name="wavelength", finished=True)

        for observation in store.stellar:
            try:
                calibrate_stellar(observation)
            except Exception as exc:
                print(f"Error: cannot perform wavelength calibration for {observation.fits_file}: {exc}")

        if self.fits_2d_norm or self.ascii_2d_norm or self.ascii_1d_norm:
            if reporter:
                reporter.set_status(name="normalize", finished=False)

            for observation in store.stellar:
                try:
                    normalize(observation)
                except Exception as exc:
                    print(f"Error: cannot normalize {observation.fits_file}: {exc}")

            if reporter:
                reporter.set_status(name="normalize", finished=True)

        if self.ascii_1d_norm:
            if reporter:
                reporter.set_status(name="stitch", finished=False)

            for observation in store.stellar:
                try:
                    stitch_oned(observation)
                except Exception as exc:
                    print(f"Error: cannot create 1D spectrum for {observation.fits_file}: {exc}")

            if reporter:
                reporter.set_status(name="stitch", finished=True)

        if reporter:
            reporter.set_stellar(store.stellar)
            reporter.set_status(name="save", finished=False)

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

        if reporter:
            reporter.set_status(name="save", finished=True)

        if reporter:
            reporter.set_finished()

        if show_files_when_done:
            open_directory(store.output_directory)
