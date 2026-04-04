from pathlib import Path
from typing import Any

from despero.apall import extract_2d_spectra, find_orders_coordinates
from despero.calibrate import (calibrate_comp_spectra, calibrate_stellar,
                               get_comp_for_stellar, get_useful_comp_indexes)
from despero.initial_corrections import correct_for_flat
from despero.save.as_ascii import save_as_2d_ascii
from despero.store.store import Store
from despero.utils import load_comp_standard, open_directory


class InspectJob:
    def __init__(
        self,
        observation_dir: Path | str,
        flat: bool,
        flat_filename: str,
        comp_filename: str,
        stellar_filenames: list[str],
    ):
        self.observation_dir = observation_dir
        self.flat = flat
        self.flat_filename = flat_filename
        self.comp_filename = comp_filename
        self.stellar_filenames = stellar_filenames

    def start(self, reporter: Any | None = None, show_files_when_done: bool = False):
        if reporter:
            reporter.render_working_screen()

        store = Store(directory=self.observation_dir)
        if reporter:
            store.reporter = reporter

        store.create_journal_for_inspect_job(
            flat_filename=self.flat_filename,
            comp_filename=self.comp_filename,
            stellar_filenames=self.stellar_filenames,
        )

        # create master flat even if flat correction not requested:
        # this is done to better extract the order coordinates
        store.create_master_flats()

        if reporter:
            reporter.set_master_flats(store.master_flats)

        if reporter:
            reporter.set_status(name="orders", finished=False)
        find_orders_coordinates(store, use_master_flat=self.flat)

        if reporter:
            reporter.set_status(name="orders", finished=True)
            reporter.set_order_coordinates(store.order_coordinates)

        if self.flat:
            if reporter:
                reporter.set_status(name="flat", finished=False)
            for master_flat in store.master_flats:
                for observation in [observation for observation in store.stellar]:
                    try:
                        correct_for_flat(observation, master_flat)
                    except Exception as exc:
                        if reporter:
                            reporter.warning(f"Cannot apply flat correction to {observation.fits_file}: {exc}")
            if reporter:
                reporter.set_status(name="flat", finished=True)

        get_comp_for_stellar(store)

        if reporter:
            reporter.set_files_progress(all=store.stellar)
            reporter.set_status(name="spectra", finished=False)

        for observation in store.stellar:
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

        useful_comp_indexes = get_useful_comp_indexes(store)
        for comp_index, comp in enumerate(store.comp):
            if comp_index not in useful_comp_indexes:
                continue
            calibrate_comp_spectra(comp, comp_standard)

        if reporter:
            reporter.set_files_progress(all=store.stellar)
            reporter.set_status(name="wavelength", finished=True)

        for observation in store.stellar:
            try:
                reporter.set_files_progress(file=observation)
                calibrate_stellar(observation)
                reporter.set_files_progress(file=observation, done=True)
            except Exception as exc:
                if reporter:
                    reporter.warning(f"Cannot perform wavelength calibration for {observation.fits_file}: {exc}")

        for comp in store.comp:
            comp.sort_orders()

        if reporter:
            reporter.set_comp(store.comp)

        for stellar in store.stellar:
            stellar.sort_orders()

        if reporter:
            reporter.set_files_progress(all=store.stellar)
            reporter.set_stellar(store.stellar)
            reporter.set_status(name="save", finished=False)

        for observation in store.stellar:
            reporter.set_files_progress(file=observation)
            save_as_2d_ascii(observation)
            reporter.set_files_progress(file=observation, done=True)

        if reporter:
            reporter.set_status(name="save", finished=True)

        if reporter:
            reporter.set_finished()

        if show_files_when_done:
            open_directory(store.output_directory)
