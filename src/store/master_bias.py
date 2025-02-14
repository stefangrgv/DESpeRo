import os
from typing import Any

import numpy as np

from pyraf import iraf
from src.utils import generate_random_fits_filename, load_fits


class MasterBias:
    def __init__(self, store: Any, readtime: float | int):
        self.store = store
        self.readtime = readtime
        self.raw_data = None

    def create(self) -> None:
        bias_fits_files = [bias.fits_file for bias in self.store.bias if bias.readtime == self.readtime]
        procedure_input = ", ".join(bias_fits_files)
        master_bias_fits = generate_random_fits_filename()
        iraf.zerocombine(
            input=procedure_input,
            output=master_bias_fits,
            combine="median",
            reject="minmax",
            ccdtype="zero",
            process="no",
            delete="no",
            scale="median",
            nlow=0,
            nhigh=1,
            nkeep=1,
            mclip="yes",
            lsigma=3,
            hsigma=3,
            rdnoise=0,
            gain=1,
            snoise=0,
            pclip=-0.5,
            blank=0,
            mode="ql",
        )
        _, data = load_fits(master_bias_fits)
        os.remove(master_bias_fits)
        self.raw_data = data.astype(np.uint16)
