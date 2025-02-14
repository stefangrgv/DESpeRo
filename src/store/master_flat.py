import os
from typing import Any

from pyraf import iraf
from src.utils import generate_random_fits_filename, load_fits


class MasterFlat:
    def __init__(self, store: Any, readtime: float | int):
        self.store = store
        self.readtime = readtime
        self.orders = []

    def create(self) -> None:
        flat_fits_files = [flat.fits_file for flat in self.store.flat if flat.readtime == self.readtime]
        procedure_input = ", ".join(flat_fits_files)
        master_flat_fits = generate_random_fits_filename()
        iraf.flatcombine(
            input=procedure_input,
            output=master_flat_fits,
            combine="median",
            reject="avsigclip",
            ccdtype="flat",
            process="no",
            subsets="yes",
            delete="no",
            scale="median",
            nlow=1,
            nhigh=1,
            nkeep=1,
            mclip="yes",
            lsigma=3,
            hsigma=3,
            rdnoise=0,
            gain=1,
            snoise=0,
            pclip=-0.5,
            blank=1,
            mode="ql",
        )
        _, data = load_fits(master_flat_fits)
        os.remove(master_flat_fits)
        self.raw_data = data
