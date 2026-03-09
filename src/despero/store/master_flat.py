from typing import Any

import numpy as np
from astropy.io import fits


class MasterFlat:
    def __init__(self, store: Any, readtime: float | int):
        self.store = store
        self.readtime = readtime
        self.orders = []

    def create(self) -> None:
        flat_fits_files = [flat.fits_file for flat in self.store.flat if flat.readtime == self.readtime]
        flat_data = [fits.getdata(file) for file in flat_fits_files]
        master_flat = np.median(np.stack(flat_data), axis=0).astype(np.uint16)
        self.raw_data = np.squeeze(master_flat)

    def normalize(self) -> None:
        normalized_data = self.raw_data.astype(np.float32) / np.max(self.raw_data)
        self.normalized_data = normalized_data[normalized_data < 0.01] = 1  # discard dead pixels
