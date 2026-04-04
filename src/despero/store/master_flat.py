from typing import Any

from scipy import stats
import numpy as np
from astropy.io import fits
from despero.parameters import APERTURE_HEIGHT

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
        # mask the orders (otherwise median is bias level)
        mask = np.empty(shape=self.raw_data.shape)
        mask[:] = np.nan
        for coordinates in self.store.order_coordinates:
            for i in range(len(coordinates.rows)):
                row = int(coordinates.rows[i])
                column = int(coordinates.columns[i])
                for j in range(0, APERTURE_HEIGHT):
                    if row + j < self.raw_data.shape[0]:
                        mask[row + j][column] = self.raw_data[row + j][column]
                    if row - j >= 0:
                        mask[row - j][column] = self.raw_data[row - j][column]
        normalized_data = mask / np.nanmedian(mask)
        normalized_data[normalized_data < 0.01] = 1  # discard pixels with no signal
        self.normalized_data = normalized_data
