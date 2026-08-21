import json
import os
from pathlib import Path
from typing import Any

from astropy.io import fits


def _header_to_dict(header: fits.Header) -> dict:
    """
    Convert a FITS header into a dictionary while preserving
    COMMENT and HISTORY ordering/content.

    Multiple COMMENT/HISTORY cards are concatenated into lists.
    """

    result = {}

    for card in header.cards:
        key = card.keyword
        value = card.value

        # preserve multiple COMMENT/HISTORY entries
        if key in ("COMMENT", "HISTORY"):
            result.setdefault(key, []).append(value)
            continue

        # avoid overwriting duplicate non-standard keys
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value

    return result


def save_as_1d_ascii_norm(observation: Any) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.stem.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "1d"
    os.makedirs(output_dir, exist_ok=True)

    # save spectrum
    with open(f"{output_dir}/{output_filename_base}.txt", "w") as f:
        f.write("#WAVELENGTH\tINTENSITY\n")
        for i in range(len(observation.oned_wavelength)):
            f.write(f"{observation.oned_wavelength[i]:.10f}\t{observation.oned_intensity[i]:.10f}\n")

    # save header
    header_dict = _header_to_dict(observation.header)
    with open(f"{output_dir}/{output_filename_base}_header.json", "w") as f:
        json.dump(header_dict, f, indent=4)


def save_as_2d_ascii(observation: Any, normalized: bool = False) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.stem.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "2d"
    if normalized:
        output_dir = output_dir / "ascii_normalized" / output_filename_base
    else:
        output_dir = output_dir / "ascii" / output_filename_base

    os.makedirs(output_dir, exist_ok=True)

    # save spectrum
    for n, order in enumerate(observation.orders):
        output_filename = f"{output_filename_base}_order_{n + 1}"
        with open(f"{output_dir}/{output_filename}.txt", "w") as f:
            if normalized:
                f.write("#WAVELENGTH\tNORMALIZED INTENSITY\n")
                for i in range(len(order.wavelength)):
                    f.write(f"{order.wavelength[i]:.10f}\t{order.normalized_intensity[i]:.10f}\n")
            else:
                f.write("#WAVELENGTH\tINTENSITY\n")
                for i in range(len(order.wavelength)):
                    f.write(f"{order.wavelength[i]:.10f}\t{order.intensity[i]:.10f}\n")

    # save header
    header_dict = _header_to_dict(observation.header)
    with open(f"{output_dir}/{output_filename_base}_header.json", "w") as f:
        json.dump(header_dict, f, indent=4)

def save_uncalibrated(observation: Any):
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.stem.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "uncal" / output_filename_base
    output_dir.mkdir(parents=True, exist_ok=True)

    for n, order in list(reversed(enumerate(observation.orders))):
        output_filename = f"{output_filename_base}_order_{n + 1}"
        with open(f"{output_dir}/{output_filename}.txt", "w") as f:
            f.write("#COLUMN\tINTENSITY\n")
            for i, col in enumerate(order.coordinates.columns):
                intensity = order.intensity[i]
                f.write(f"{col}\t{intensity}\n")