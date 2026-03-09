from typing import Any

import numpy as np
from astropy.io import fits


class MasterBias:
    def __init__(self, store: Any, readtime: float | int):
        self.store = store
        self.readtime = readtime
        self.raw_data = None

    def create(self) -> None:
        bias_fits_files = [bias.fits_file for bias in self.store.bias if bias.readtime == self.readtime]
        bias_data = [fits.getdata(file) for file in bias_fits_files]
        master_bias = np.median(np.stack(bias_data), axis=0).astype(np.uint16)
        self.raw_data = np.squeeze(master_bias)
