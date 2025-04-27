import os
from datetime import datetime

import numpy as np

from src import utils
from src.store.master_bias import MasterBias
from src.store.master_flat import MasterFlat
from src.store.observation import Observation


class Store:
    def __init__(self, directory: str):
        self.directory = directory

        # individual exposures
        self.bias = []
        self.flat = []
        self.comp = []
        self.stellar = []
        self.order_coordinates = []

        # combined technical images
        self.master_biases = []
        self.master_flats = []

    def load_journal_from_file(self) -> None:
        journal_path = os.path.join(self.directory, "Journal.txt")
        try:
            _fits, _dates, _exp, _exposure_type = np.loadtxt(journal_path, dtype="str", unpack=True)
        except FileNotFoundError:
            print(f"Fatal error: Journal.txt not found in {self.directory}")
            import sys

            sys.exit(1)
        for i in range(len(_fits)):
            fits_file = os.path.join(self.directory, f"{_fits[i]}.fits")
            date = datetime.strptime(_dates[i], "%Y-%m-%dT%H:%M:%S")
            exposure_time = float(_exp[i])
            (readtime, rdnoise) = utils.get_readtime_and_readnoise(fits_file)
            if _exposure_type[i] == "object":
                exposure_type = utils.EXPOSURE_TYPES.STELLAR
                target_array = self.stellar
            elif _exposure_type[i] == "zero":
                exposure_type = utils.EXPOSURE_TYPES.BIAS
                target_array = self.bias
            elif _exposure_type[i] == "flat":
                exposure_type = utils.EXPOSURE_TYPES.FLAT
                target_array = self.flat
            elif _exposure_type[i] == "comp":
                exposure_type = utils.EXPOSURE_TYPES.COMP
                target_array = self.comp
            observation = Observation(self, fits_file, exposure_type, date, exposure_time, readtime, rdnoise)
            target_array.append(observation)

    def create_master_biases(self) -> None:
        for readtime in list(set([bias.readtime for bias in self.bias])):
            print(f"\tCreating master bias for readtime = {readtime}...")
            master_bias = MasterBias(self, readtime)
            master_bias.create()
            self.master_biases.append(master_bias)

    def _get_corresponding_master_bias(self, readtime: int | float) -> MasterBias | None:
        for bias in self.master_biases:
            if bias.readtime == readtime:
                return bias

    def create_master_flats(self) -> None:
        for readtime in list(set([flat.readtime for flat in self.flat])):
            print(f"\tCreating master flat for readtime = {readtime}...")
            master_flat = MasterFlat(self, readtime)
            master_flat.create()

            corresponding_master_bias = self._get_corresponding_master_bias(readtime)
            if corresponding_master_bias is not None:
                target_data = master_flat.raw_data.astype(np.int64)
                target_data -= corresponding_master_bias.raw_data
                master_flat.raw_data = np.clip(target_data, 0, 2**16).astype(np.uint16)
            master_flat.normalize()
            self.master_flats.append(master_flat)
