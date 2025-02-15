import os
import tkinter as tk
from tkinter import BooleanVar, StringVar, messagebox
from tkinter.filedialog import askdirectory

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
from src.store.store import Store
from src.utils import add_vhelio_to_fits

NO_DIR_STRING = "No selected directory"


class UI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ESpeRo DRS")

        self.observations_dir = StringVar()
        self.observations_dir_truncated = StringVar()
        self.observations_dir_truncated.set(NO_DIR_STRING)

        self.cosmic = BooleanVar()
        self.cosmic.set(True)

        self.bias = BooleanVar()
        self.bias.set(True)

        self.flat = BooleanVar()
        self.flat.set(True)

        self.vhelio = BooleanVar()
        self.vhelio.set(True)

    def draw(self) -> None:
        # frames
        container = tk.Frame(self.root)
        container.pack(expand=True)

        dir_frame = tk.Frame(container)
        dir_frame.pack(pady=10, anchor="w")

        config_frame = tk.Frame(container)
        config_frame.pack(pady=10, anchor="w")

        start_frame = tk.Frame(container)
        start_frame.pack(pady=10, anchor="w", fill="x", expand=True)

        # elements
        directory_label = tk.Label(dir_frame, textvariable=self.observations_dir_truncated)
        directory_label.pack(side=tk.LEFT, padx=5)

        select_button = tk.Button(dir_frame, text="Select", command=self.select_directory)
        select_button.pack(side=tk.RIGHT, padx=5)

        self.cosmic_checkbox = tk.Checkbutton(config_frame, text="Remove cosmics", variable=self.cosmic)
        self.cosmic_checkbox.pack(pady=5, anchor="w")

        self.bias_checkbox = tk.Checkbutton(config_frame, text="Correct for bias", variable=self.bias)
        self.bias_checkbox.pack(pady=5, anchor="w")
        self.bias_checkbox.config(state=tk.DISABLED)

        self.flat_checkbox = tk.Checkbutton(config_frame, text="Correct for flat", variable=self.flat)
        self.flat_checkbox.pack(pady=5, anchor="w")
        self.flat_checkbox.config(state=tk.DISABLED)

        self.vhelio_checkbox = tk.Checkbutton(config_frame, text="Correct for VHELIO", variable=self.vhelio)
        self.vhelio_checkbox.pack(pady=5, anchor="w")
        self.vhelio_checkbox.config(state=tk.DISABLED)

        self.start_button = tk.Button(start_frame, text="GO", command=self.go)
        self.start_button.pack(fill="x", expand=True)
        self.start_button.config(state=tk.DISABLED)

        self.set_settings(state=False)
        self.root.minsize(500, 300)
        self.root.mainloop()

    def select_directory(self) -> None:
        observations_dir = askdirectory()
        if not observations_dir:
            return
        if "Journal.txt" in os.listdir(observations_dir):
            self.observations_dir.set(observations_dir)
            self.observations_dir_truncated.set(f".../{os.path.split(observations_dir)[-1]}")
            self.set_settings(True)
        else:
            messagebox.showerror("Error", "No Journal.txt file!\nRun FitsMEdit first.")

    def set_settings(self, state: bool) -> None:
        for setting in [
            self.cosmic_checkbox,
            self.bias_checkbox,
            self.flat_checkbox,
            self.vhelio_checkbox,
            self.start_button,
        ]:
            setting.config(state=(tk.ACTIVE if state else tk.DISABLED))

    def go(self) -> None:
        self.root.destroy()

        store = Store(self.observations_dir.get())
        store.load_journal_from_file()

        if self.bias.get() or self.flat.get() or self.vhelio.get():
            iraf.noao()
            iraf.rv()
            iraf.imred()
            iraf.ccd()

        if self.cosmic.get():
            clean_cosmics(store)

        if self.vhelio.get():
            add_vhelio_to_fits(store)

        if self.bias.get():
            # fix bias correction
            store.create_master_biases()
            correct_for_bias(store)

        if self.flat.get():
            store.create_master_flats()
            find_orders_coordinates(store, use_master_flat=True)
            correct_for_flat(store)
        else:
            find_orders_coordinates(store, use_master_flat=False)

        extract_2d_spectra(
            store,
            [*store.comp, *store.stellar],
        )
        calibrate_comp_spectra(store)
        get_comp_for_stellar(store)
        calibrate_stellar(store)

        if self.vhelio.get():
            correct_for_vhelio(store)

        normalize(store)
        # stitch_oned(store)
        import pdb

        pdb.set_trace()


if __name__ == "__main__":
    ui = UI()
    ui.draw()
