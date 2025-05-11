import json
import os
import subprocess
import sys
from enum import Enum

import numpy as np
from astropy.io import fits

from src.store.order import Order
from src.store.order_coordinates import OrderCoordinates


class EXPOSURE_TYPES(Enum):
    STELLAR = 0
    COMP = 1
    BIAS = 2
    FLAT = 3


def load_fits(fits_file_path: str) -> tuple[dict, np.ndarray]:
    with fits.open(fits_file_path) as hdul:
        header = hdul[0].header
        data = hdul[0].data
        data = np.squeeze(data, axis=0)
    return (header, data)


def get_technical_apertures_path(fits_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.realpath(fits_path)), "apertures.npy")


def load_npy_spectrum(fpath: str) -> np.ndarray:
    return np.load(fpath, allow_pickle=True).item()


def get_readtime_and_readnoise(
    fpath: str,
) -> tuple[int | float, int | float]:
    header, _ = load_fits(fpath)
    return (header["READTIME"], header["RDNOISE"])


def get_readtimes(journal: list[dict]) -> list[int | float]:
    return list(set([spec["readtime"] for spec in journal]))


class ObservationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Order):
            return {"intensity": [int(i) for i in obj.intensity], "coordinates": obj.coordinates}
        elif isinstance(obj, OrderCoordinates):
            return {
                "number": obj.number,
                "columns": obj.columns.tolist(),
                "rows": obj.rows.tolist(),
                "points": getattr(obj, "points", []),
            }
        return super().default(obj)


def open_directory(path):
    if sys.platform.startswith("darwin"):  # macOS
        subprocess.run(["open", path], check=True)
    elif os.name == "nt":  # Windows
        os.startfile(path)
    elif os.name == "posix":  # Linux / Unix
        subprocess.run(["xdg-open", path], check=True)
    else:
        raise OSError("Unsupported operating system")
