import os
import threading
import tkinter as tk
from tkinter import BooleanVar, StringVar, messagebox
from tkinter.filedialog import askdirectory

from src.drs_run import DRS_Run

NO_DIR_STRING = "No selected directory"
BACKGROUND_COLORS = {"MAIN": "#ebebeb", "BUTTON": "#e0e0e0"}


class UI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DESpeRo")
        self.root.config(bg=BACKGROUND_COLORS["MAIN"])

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
        self.container_frame = tk.Frame(self.root, bg=BACKGROUND_COLORS["MAIN"])
        self.container_frame.pack(expand=True, padx=30, pady=10)

        dir_frame = tk.Frame(self.container_frame, bg=BACKGROUND_COLORS["MAIN"])
        dir_frame.pack(anchor="w")

        self.config_frame = tk.Frame(self.container_frame, bg=BACKGROUND_COLORS["MAIN"])
        self.config_frame.pack(pady=10, anchor="w")

        self.output_frame = tk.Frame(self.container_frame, bg=BACKGROUND_COLORS["MAIN"])
        self.output_frame.pack(pady=10, anchor="w")

        self.start_frame = tk.Frame(self.container_frame, bg=BACKGROUND_COLORS["MAIN"])
        self.start_frame.pack(pady=10, anchor="w", fill="x", expand=True)

        # elements
        directory_label = tk.Label(
            dir_frame, textvariable=self.observations_dir_truncated, bg=BACKGROUND_COLORS["MAIN"]
        )
        directory_label.pack(side=tk.LEFT, padx=5)

        self.select_button = tk.Button(
            dir_frame, text="Select", command=self._select_directory, bg=BACKGROUND_COLORS["BUTTON"]
        )
        self.select_button.pack(side=tk.RIGHT, padx=5)

        self.cosmic_checkbox = tk.Checkbutton(
            self.config_frame,
            text="Remove cosmics",
            variable=self.cosmic,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.cosmic_checkbox.pack(pady=5, anchor="w")

        self.bias_checkbox = tk.Checkbutton(
            self.config_frame,
            text="Correct for bias",
            variable=self.bias,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.bias_checkbox.pack(pady=5, anchor="w")
        self.bias_checkbox.config(state=tk.DISABLED)

        self.flat_checkbox = tk.Checkbutton(
            self.config_frame,
            text="Correct for flat",
            variable=self.flat,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.flat_checkbox.pack(pady=5, anchor="w")
        self.flat_checkbox.config(state=tk.DISABLED)

        self.vhelio_checkbox = tk.Checkbutton(
            self.config_frame,
            text="Correct for VHELIO",
            variable=self.vhelio,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.vhelio_checkbox.pack(pady=5, anchor="w")
        self.vhelio_checkbox.config(state=tk.DISABLED)

        output_text = tk.StringVar()
        output_text.set("Output format")
        output_label = tk.Label(self.output_frame, textvariable=output_text, bg=BACKGROUND_COLORS["MAIN"])
        output_label.pack(pady=5, anchor="w")

        self.fits_2d_checkbox = tk.Checkbutton(
            self.output_frame, text="2D FITS", variable=self.fits_2d, bg=BACKGROUND_COLORS["MAIN"], highlightthickness=0
        )
        self.fits_2d_checkbox.pack(pady=5, anchor="w")
        self.fits_2d_checkbox.config(state=tk.DISABLED)

        self.fits_2d_norm_checkbox = tk.Checkbutton(
            self.output_frame,
            text="2D FITS (normalized)",
            variable=self.fits_2d_norm,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.fits_2d_norm_checkbox.pack(pady=5, anchor="w")
        self.fits_2d_norm_checkbox.config(state=tk.DISABLED)

        self.ascii_2d_checkbox = tk.Checkbutton(
            self.output_frame,
            text="2D ASCII",
            variable=self.ascii_2d,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.ascii_2d_checkbox.pack(pady=5, anchor="w")
        self.ascii_2d_checkbox.config(state=tk.DISABLED)

        self.ascii_2d_norm_checkbox = tk.Checkbutton(
            self.output_frame,
            text="2D ASCII (normalized)",
            variable=self.ascii_2d_norm,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.ascii_2d_norm_checkbox.pack(pady=5, anchor="w")
        self.ascii_2d_norm_checkbox.config(state=tk.DISABLED)

        self.ascii_1d_norm_checkbox = tk.Checkbutton(
            self.output_frame,
            text="1D ASCII (normalized)",
            variable=self.ascii_1d_norm,
            bg=BACKGROUND_COLORS["MAIN"],
            highlightthickness=0,
        )
        self.ascii_1d_norm_checkbox.pack(pady=5, anchor="w")
        self.ascii_1d_norm_checkbox.config(state=tk.DISABLED)

        self.start_button = tk.Button(self.start_frame, text="GO", command=self._go, bg=BACKGROUND_COLORS["BUTTON"])
        self.start_button.pack(fill="x", expand=True)
        self.start_button.config(state=tk.DISABLED)

        self._set_settings(state=False)
        self.root.mainloop()

    def set_status(self, name: str, finished: bool) -> None:
        color = "#147800" if finished else "black"
        label = None
        for l in self.steps_labels:
            if l["name"] == name:
                label = l["label"]
                break
        if label is None:
            return
        label.config(fg=color)

    def render_working_screen(self):
        self.config_frame.destroy()
        self.output_frame.destroy()
        self.start_frame.destroy()
        self.select_button.destroy()

        self.status_frame = tk.Frame(self.container_frame, bg=BACKGROUND_COLORS["MAIN"])
        self.status_frame.pack(anchor="w", fill="x", pady=10)

        self._init_steps_labels()

    def _create_status_label(self, text: str):
        return tk.Label(
            master=self.status_frame,
            fg="#949292",
            bg=BACKGROUND_COLORS["MAIN"],
            textvariable=tk.StringVar(master=self.status_frame, value=text),
        )

    def _init_steps_labels(self):
        self.steps_labels = []

        if self.cosmic.get():
            self.steps_labels.append(
                {
                    "name": "cosmics",
                    "label": self._create_status_label("Clean cosmics"),
                }
            )
        if self.bias.get():
            self.steps_labels.append(
                {
                    "name": "bias",
                    "label": self._create_status_label("Correct for bias"),
                }
            )
        if self.flat.get():
            self.steps_labels.append(
                {
                    "name": "flat",
                    "label": self._create_status_label("Correct for flat"),
                }
            )
        self.steps_labels.append(
            {
                "name": "orders",
                "label": self._create_status_label("Trace echelle orders"),
            }
        )
        self.steps_labels.append(
            {
                "name": "spectra",
                "label": self._create_status_label("Extract spectra"),
            }
        )
        self.steps_labels.append(
            {
                "name": "wavelength",
                "label": self._create_status_label("Calibrate for wavelength"),
            }
        )
        if self.fits_2d_norm.get() or self.ascii_2d_norm.get() or self.ascii_1d_norm.get():
            self.steps_labels.append(
                {
                    "name": "normalize",
                    "label": self._create_status_label("Normalize spectra"),
                }
            )
        if self.ascii_1d_norm.get():
            self.steps_labels.append(
                {
                    "name": "stitch",
                    "label": self._create_status_label("Stitch spectra"),
                }
            )
        self.steps_labels.append(
            {
                "name": "save",
                "label": self._create_status_label("Save files"),
            }
        )

        for steps_label in self.steps_labels:
            steps_label["label"].pack(anchor="w")

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
        ]:
            setting.config(state=(tk.ACTIVE if state else tk.DISABLED))

    def _go(self) -> None:
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
        thread = threading.Thread(target=drs_run.start, args=(self,))
        thread.start()
