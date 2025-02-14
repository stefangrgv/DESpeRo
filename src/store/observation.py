from typing import Any

from src.utils import load_fits


class Observation:
    def __init__(
        self,
        store: Any,
        fits_file: str,
        exposure_type: Any,
        date: Any,
        exposure_time: float | int,
        readtime: float | int,
        rdnoise: float | int,
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

        _, raw_data = load_fits(self.fits_file)
        self.raw_data = raw_data
