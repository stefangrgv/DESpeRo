from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.time import Time

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
        gain: float | int | None = None,
        load: bool = True,
    ):
        self.store = store
        self.fits_file = fits_file
        self.exposure_type = exposure_type
        self.date = date
        self.exposure_time = exposure_time
        self.readtime = readtime
        self.rdnoise = rdnoise
        self.gain = gain
        self.variance = None  # per-pixel variance image (ADU^2), see initial_corrections.init_variance
        self.vhelio = None
        self.jd = None
        self.orders = []
        self.wavelength_calibrated = False
        self.oned_wavelength = []
        self.oned_intensity = []
        self.oned_intensity_error = []

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

            if self.gain is None:
                self.gain = self.header.get("GAIN", None)

            if exposure_type == EXPOSURE_TYPES.STELLAR:
                try:
                    self.ra = self.header["RA"]
                    self.dec = self.header["DEC"]
                    self.jd = float(self.header["JD-OBS"])
                except KeyError as exc:
                    self._warn(str(exc))
                if any(key.startswith("IMCMB") for key in self.header):
                    self._set_jd_from_combined_inputs()
                self._check_jd_matches_night()

    def _warn(self, text: str) -> None:
        if self.store.reporter:
            self.store.reporter.warning(text)

    def _set_jd_from_combined_inputs(self) -> None:
        """
        A combined frame (e.g. IRAF imcombine) carries the combine date in DATE-OBS/JD-OBS,
        so take the exposure-weighted mean of the input frames' mid-exposure JD-OBS instead.
        """
        inputs = [value for key, value in self.header.items() if key.startswith("IMCMB")]
        jds, weights, dates = [], [], []
        try:
            for name in inputs:
                input_header = fits.getheader(self.fits_file.parent / name)
                jds.append(float(input_header["JD-OBS"]))
                weights.append(float(input_header.get("EXPTIME", 1.0)))
                dates.append(input_header.get("DATE-OBS"))
        except (OSError, KeyError, ValueError) as exc:
            self._warn(
                f"{self.fits_file.name} is a combined frame but its input {name} cannot be read ({exc}); "
                "its JD-OBS is unreliable, skipping VHELIO correction"
            )
            self.jd = None
            return

        self.jd = float(np.average(jds, weights=weights))
        self.header["JD-COMB"] = (self.header.get("JD-OBS"), "JD-OBS of the combined frame as written")
        self.header["JD-OBS"] = (self.jd, "exposure-weighted mean JD-OBS of the inputs")
        if dates[int(np.argmin(jds))]:
            self.header["DATE-OBS"] = dates[int(np.argmin(jds))]
        self.header["HISTORY"] = f"JD-OBS, DATE-OBS taken from the {len(inputs)} combined input frames"

    def _check_jd_matches_night(self) -> None:
        """Warn when JD-OBS is outside the night named by the observation directory (YYYY-MM-DD, evening date)."""
        if self.jd is None:
            return
        try:
            night = datetime.strptime(Path(self.store.directory).name, "%Y-%m-%d")
        except ValueError:
            return
        night_start = Time(night.replace(hour=12)).jd
        if not night_start <= self.jd < night_start + 1:
            header_date = Time(self.jd, format="jd").isot[:19]
            self._warn(
                f"{self.fits_file.name}: JD-OBS {self.jd:.5f} ({header_date}) is outside the night "
                f"{night.date()}; the VHELIO correction uses the header time"
            )

    def normalize(self) -> None:
        normalized_data = self.raw_data.astype(np.float32) / np.max(self.raw_data)
        normalized_data[normalized_data < 0.01] = 1  # discard dead pixels
        self.normalized_data = normalized_data

    def sort_orders(self) -> None:
        self.orders = [order for order in reversed(self.orders)]
