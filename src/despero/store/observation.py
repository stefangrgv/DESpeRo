from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from despero.utils import EXPOSURE_TYPES, load_fits


class Observation:
    def __init__(
        self,
        store: Any,
        fits_file: Path,
        exposure_type: Any,
        date: Any,
        exposure_time: float | int,
        readtime: float | int | None = None,
        rdnoise: float | int | None = None,
        load: bool = True,
    ):
        self.store = store
        self.fits_file = fits_file
        self.exposure_type = exposure_type
        self.date = date
        self.exposure_time = exposure_time
        self.readtime = readtime
        self.rdnoise = rdnoise
        self.vhelio = None
        self.orders = []
        self.wavelength_calibrated = False
        self.oned_wavelength = []
        self.oned_intensity = []

        if load:
            header, raw_data = load_fits(self.fits_file)
            self.raw_data = raw_data.astype(np.float32)
            self.header = header
            today = date.today().isoformat()
            self.header["HISTORY"] = f"Reduced by DESpeRo on {today}"

            if self.readtime is None:
                self.readtime = self.header.get("READTIME", None)

            if self.rdnoise is None:
                self.rdnoise = self.header.get("RDNOISE", None)

            if exposure_type == EXPOSURE_TYPES.STELLAR:
                try:
                    self.ra = self.header["RA"]
                    self.dec = self.header["DEC"]
                    self.jd = self.header["JD-OBS"]
                except KeyError as exc:
                    if self.store.reporter:
                        self.store.reporter.warning(str(exc))

    def normalize(self) -> None:
        normalized_data = self.raw_data.astype(np.float32) / np.max(self.raw_data)
        normalized_data[normalized_data < 0.01] = 1  # discard dead pixels
        self.normalized_data = normalized_data

    def sort_orders(self) -> None:
        self.orders = [order for order in reversed(self.orders)]
