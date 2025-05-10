import os
import tkinter as tk
from tkinter import BooleanVar, StringVar, messagebox
from tkinter.filedialog import askdirectory

from src.drs_run import DRS_Run

NO_DIR_STRING = "No selected directory"


class UI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DESpeRo")

    def render_welcome_screen(self) -> None:
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

        self.fits_2d = BooleanVar()
        self.fits_2d.set(False)

        self.fits_2d_norm = BooleanVar()
        self.fits_2d_norm.set(False)

        self.ascii_2d = BooleanVar()
        self.ascii_2d.set(False)

        self.ascii_2d_norm = BooleanVar()
        self.ascii_2d_norm.set(False)

        self.ascii_1d_norm = BooleanVar()
        self.ascii_1d_norm.set(False)

        self.output_vars = [self.fits_2d, self.fits_2d_norm, self.ascii_2d, self.ascii_2d_norm, self.ascii_1d_norm]
        for var in self.output_vars:
            var.trace_add("write", lambda *args: self._update_start_button_state())

        # frames
        container = tk.Frame(self.root)
        container.pack(expand=True)

        dir_frame = tk.Frame(container)
        dir_frame.pack(pady=10, anchor="w")

        config_frame = tk.Frame(container)
        config_frame.pack(pady=10, anchor="w")

        output_frame = tk.Frame(container)
        output_frame.pack(pady=10, anchor="w")

        start_frame = tk.Frame(container)
        start_frame.pack(pady=10, anchor="w", fill="x", expand=True)

        # elements
        directory_label = tk.Label(dir_frame, textvariable=self.observations_dir_truncated)
        directory_label.pack(side=tk.LEFT, padx=5)

        select_button = tk.Button(dir_frame, text="Select", command=self._select_directory)
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

        output_text = tk.StringVar()
        output_text.set("Output format")
        output_label = tk.Label(output_frame, textvariable=output_text)
        output_label.pack(pady=5, anchor="w")

        self.fits_2d_checkbox = tk.Checkbutton(output_frame, text="2D FITS", variable=self.fits_2d)
        self.fits_2d_checkbox.pack(pady=5, anchor="w")
        self.fits_2d_checkbox.config(state=tk.DISABLED)

        self.fits_2d_norm_checkbox = tk.Checkbutton(
            output_frame, text="2D FITS (normalized)", variable=self.fits_2d_norm
        )
        self.fits_2d_norm_checkbox.pack(pady=5, anchor="w")
        self.fits_2d_norm_checkbox.config(state=tk.DISABLED)

        self.ascii_2d_checkbox = tk.Checkbutton(output_frame, text="2D ASCII", variable=self.ascii_2d)
        self.ascii_2d_checkbox.pack(pady=5, anchor="w")
        self.ascii_2d_checkbox.config(state=tk.DISABLED)

        self.ascii_2d_norm_checkbox = tk.Checkbutton(
            output_frame, text="2D ASCII (normalized)", variable=self.ascii_2d_norm
        )
        self.ascii_2d_norm_checkbox.pack(pady=5, anchor="w")
        self.ascii_2d_norm_checkbox.config(state=tk.DISABLED)

        self.ascii_1d_norm_checkbox = tk.Checkbutton(
            output_frame, text="1D ASCII (normalized)", variable=self.ascii_1d_norm
        )
        self.ascii_1d_norm_checkbox.pack(pady=5, anchor="w")
        self.ascii_1d_norm_checkbox.config(state=tk.DISABLED)

        self.start_button = tk.Button(start_frame, text="GO", command=self._go)
        self.start_button.pack(fill="x", expand=True)
        self.start_button.config(state=tk.DISABLED)

        self._set_settings(state=False)
        self.root.minsize(500, 300)
        self.root.mainloop()

    def _update_start_button_state(self):
        if any(var.get() for var in self.output_vars):
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)

    def _select_directory(self) -> None:
        observations_dir = askdirectory()
        if not observations_dir:
            return
        if "Journal.txt" in os.listdir(observations_dir):
            self.observations_dir.set(observations_dir)
            self.observations_dir_truncated.set(f".../{os.path.split(observations_dir)[-1]}")
            self._set_settings(True)
        else:
            messagebox.showerror("Error", "No Journal.txt file!\nRun FitsMEdit first.")

    def _set_settings(self, state: bool) -> None:
        for setting in [
            self.cosmic_checkbox,
            self.bias_checkbox,
            self.flat_checkbox,
            self.vhelio_checkbox,
            self.fits_2d_checkbox,
            self.fits_2d_norm_checkbox,
            self.ascii_2d_checkbox,
            self.ascii_2d_norm_checkbox,
            self.ascii_1d_norm_checkbox,
            self.start_button,
        ]:
            setting.config(state=(tk.ACTIVE if state else tk.DISABLED))

    def _go(self) -> None:
        self.root.destroy()
        self.root.quit()
        drs_run = DRS_Run(
            observation_dir=self.observations_dir.get(),
            cosmic=self.cosmic.get(),
            bias=self.bias.get(),
            flat=self.flat.get(),
            vhelio=self.vhelio.get(),
            fits_2d=self.fits_2d.get(),
            fits_2d_norm=self.fits_2d_norm.get(),
            ascii_2d=self.ascii_2d.get(),
            ascii_2d_norm=self.ascii_2d_norm.get(),
            ascii_1d_norm=self.ascii_1d_norm.get(),
        )
        drs_run.start()
