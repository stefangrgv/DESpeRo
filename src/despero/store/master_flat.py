from typing import Any

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
        mask = np.empty(shape=self.raw_data.shape)
        mask[:] = np.nan

        for coordinates in self.store.order_coordinates:
            for i in range(len(coordinates.rows)):
                row = int(coordinates.rows[i])
                column = int(coordinates.columns[i])

                for j in range(APERTURE_HEIGHT + 1):
                    if row + j < self.raw_data.shape[0]:
                        mask[row + j, column] = self.raw_data[row + j, column]
                    if row - j >= 0:
                        mask[row - j, column] = self.raw_data[row - j, column]

        # Column-wise median ignoring NaNs
        col_median = np.nanmedian(mask, axis=0)

        # avoid division by zero / tiny values
        epsilon = 0.05 * np.nanmedian(col_median)
        col_median = np.where(np.isnan(col_median) | (col_median < epsilon), epsilon, col_median)

        self.normalized_data = mask / col_median
