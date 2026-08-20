import numpy as np
from pathlib import Path
from typing import Any

from despero.apall import extract_2d_spectra, find_orders_coordinates, set_order_coordinates_from_file
from despero.calibrate import (calibrate_comp_spectra, calibrate_stellar,
                               get_comp_for_stellar, get_useful_comp_indexes)
from despero.initial_corrections import (clean_cosmics, correct_for_bias,
                                         correct_for_flat)
from despero.normalize import normalize, stitch_oned
from despero.save.as_ascii import save_as_1d_ascii_norm, save_as_2d_ascii
from despero.save.as_fits import save_as_fits
from despero.store.store import Store
from despero.utils import load_comp_standard, open_directory
from despero.vhelio import correct_vhelio


class Job:
    def __init__(
        self,
        observation_dir: Path | str,
        order_file: str,
        cosmic: bool = False,
        bias: bool = False,
        flat: bool = False,
        vhelio: bool = False,
        fits_2d: bool = False,
        fits_2d_norm: bool = False,
        ascii_2d: bool = False,
        ascii_2d_norm: bool = False,
        ascii_1d_norm: bool = False,
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
        self.order_file = order_file
        self.store = Store(directory=self.observation_dir)


    def _get_raw_data(self, observation: Any) -> list[int]:
        return observation.raw_data.tolist()

    def prepare(self, reporter: Any | None = None):
        if reporter:
            self.store.reporter = reporter

        self.store.load_journal_from_file()
        self.store.create_master_flats()
        raw_data = {}
        for i, observation in enumerate(self.store.master_flats):
            raw_data[f"master_flat_{i}"] = self._get_raw_data(observation)
        for observation in self.store.stellar:
            raw_data[observation.fits_file.stem] = self._get_raw_data(observation)
        return {"raw_data": raw_data}


    def start(self, reporter: Any | None = None, show_files_when_done: bool = False):
        if reporter:
            self.store.reporter = reporter

        self.store.load_journal_from_file()

        if reporter:
            reporter.render_working_screen()

        if self.cosmic:
            if reporter:
                reporter.set_files_progress(all=self.store.stellar)
                reporter.set_status(name="cosmics", finished=False)

            for observation in self.store.stellar:
                try:
                    reporter.set_files_progress(file=observation)
                    clean_cosmics(observation)
                    reporter.set_files_progress(file=observation, done=True)
                except Exception as exc:
                    if reporter:
                        reporter.warning(f"Cannot clean cosmics from {observation.fits_file}: {exc}")
            if reporter:
                reporter.set_status(name="cosmics", finished=True)

        if self.bias:
            if reporter:
                reporter.set_status(name="bias", finished=False)

            self.store.create_master_biases()
            observations_to_correct_for_bias = [*self.store.flat, *self.store.comp, *self.store.stellar]
            for master_bias in self.store.master_biases:
                for observation in [
                    observation
                    for observation in observations_to_correct_for_bias
                    if observation.readtime == master_bias.readtime
                ]:
                    try:
                        correct_for_bias(observation, master_bias)
                    except Exception as exc:
                        if reporter:
                            reporter.warning(f"Cannot apply bias correction to {observation.fits_file}: {exc}")

            if reporter:
                reporter.set_status(name="bias", finished=True)

        self.store.create_master_flats()

        if reporter:
            reporter.set_status(name="orders", finished=False)
        if self.order_file:
            set_order_coordinates_from_file(self.store, self.order_file)
        else:
            find_orders_coordinates(self.store)

        if reporter:
            reporter.set_status(name="orders", finished=True)
            reporter.set_order_coordinates(self.store.order_coordinates)

        for master_flat in self.store.master_flats:
            master_flat.normalize()

        if self.flat:
            if reporter:
                reporter.set_status(name="flat", finished=False)

            for observation in [
                observation for observation in self.store.stellar if observation.readtime == master_flat.readtime
            ]:
                try:
                    correct_for_flat(observation, master_flat)
                except Exception as exc:
                    if reporter:
                        reporter.warning(f"Cannot apply flat correction to {observation.fits_file}: {exc}")

        if reporter:
            reporter.export_raw_data(self.store.master_flats, self.store.stellar)
            reporter.set_status(name="flat", finished=True)

        get_comp_for_stellar(self.store)

        if reporter:
            reporter.set_files_progress(all=self.store.stellar)
            reporter.set_status(name="spectra", finished=False)

        for observation in self.store.stellar:
            try:
                reporter.set_files_progress(file=observation)
                extract_2d_spectra(observation)
                reporter.set_files_progress(file=observation, done=True)
            except Exception as exc:
                if reporter:
                    reporter.warning(f"Cannot extract 2D spectrum from {observation.fits_file}: {exc}")

        if reporter:
            reporter.set_status(name="spectra", finished=True)
            reporter.set_status(name="wavelength", finished=False)

        try:
            comp_standard = load_comp_standard()
        except FileNotFoundError:
            if reporter:
                reporter.warning("Fatal error: comp standard not found!")

        if reporter:
            reporter.set_comp_standard(comp_standard)

        useful_comp_indexes = get_useful_comp_indexes(self.store)
        for comp_index, comp in enumerate(self.store.comp):
            if comp_index not in useful_comp_indexes:
                continue
            calibrate_comp_spectra(comp, comp_standard)

        if reporter:
            reporter.set_files_progress(all=self.store.stellar)
            reporter.set_status(name="wavelength", finished=True)

        for observation in self.store.stellar:
            try:
                reporter.set_files_progress(file=observation)
                calibrate_stellar(observation)
                reporter.set_files_progress(file=observation, done=True)
            except Exception as exc:
                if reporter:
                    reporter.warning(f"Cannot perform wavelength calibration for {observation.fits_file}: {exc}")

        for comp in self.store.comp:
            comp.sort_orders()

        if reporter:
            reporter.set_comp(self.store.comp)

        if self.vhelio:
            for observation in self.store.stellar:
                try:
                    correct_vhelio(observation)
                except Exception as exc:
                    if reporter:
                        reporter.warning(f"Cannot perform VHELIO correction for {observation.fits_file}: {exc}")

        if self.fits_2d_norm or self.ascii_2d_norm or self.ascii_1d_norm:
            if reporter:
                reporter.set_files_progress(all=self.store.stellar)
                reporter.set_status(name="normalize", finished=False)

            for observation in self.store.stellar:
                try:
                    reporter.set_files_progress(file=observation)
                    normalize(observation)
                    reporter.set_files_progress(file=observation, done=True)
                except Exception as exc:
                    if reporter:
                        reporter.warning(f"Cannot normalize {observation.fits_file}: {exc}")

            if reporter:
                reporter.set_status(name="normalize", finished=True)

        if self.ascii_1d_norm:
            if reporter:
                reporter.set_files_progress(all=self.store.stellar)
                reporter.set_status(name="stitch", finished=False)

            for observation in self.store.stellar:
                try:
                    reporter.set_files_progress(file=observation)
                    stitch_oned(observation)
                    reporter.set_files_progress(file=observation, done=True)
                except Exception as exc:
                    if reporter:
                        reporter.warning(f"Cannot create 1D spectrum for {observation.fits_file}: {exc}")

            if reporter:
                reporter.set_status(name="stitch", finished=True)

        for stellar in self.store.stellar:
            stellar.sort_orders()

        if reporter:
            reporter.set_stellar(self.store.stellar)
            reporter.set_files_progress(all=self.store.stellar)
            reporter.set_status(name="save", finished=False)

        for observation in self.store.stellar:
            reporter.set_files_progress(file=observation)
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
            reporter.set_files_progress(file=observation, done=True)

        if reporter:
            reporter.set_status(name="save", finished=True)

        if reporter:
            reporter.set_finished()

        if show_files_when_done:
            open_directory(self.store.output_directory)
