import os
from pathlib import Path
from typing import Any

from src.normalize import _fit_continuum


def save_as_1d_ascii_norm(observation: Any) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "1d"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/{output_filename_base}.txt", "w") as f:
        f.write("#WAVELENGTH\tINTENSITY\n")
        for i in range(len(observation.oned_wavelength)):
            f.write(f"{observation.oned_wavelength[i]:.10f}\t{observation.oned_intensity[i]:.10f}\n")


def save_as_2d_ascii(observation: Any, normalized: bool = False) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "2d"
    if normalized:
        output_dir = output_dir / "ascii_normalized" / output_filename_base
    else:
        output_dir = output_dir / "ascii" / output_filename_base

    os.makedirs(output_dir, exist_ok=True)
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


def save_uncalibrated(observation: Any) -> None:
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = Path(os.path.dirname(observation.fits_file)) / "uncalibrated" / output_filename_base
    os.makedirs(output_dir, exist_ok=True)
    for n, order in enumerate(observation.orders):
        filename = output_dir / f"{n:02d}.txt"
        with open(filename, "w") as f:
            f.write("#WAVELENGTH\tINTENSITY\n")
            for i, column in enumerate(order.coordinates.columns):
                f.write(f"{column}\t{order.intensity[i]:.10f}\n")


def save_uncalibrated_normalized(observation: Any) -> None:
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = Path(os.path.dirname(observation.fits_file)) / "uncalibrated_normalized" / output_filename_base
    os.makedirs(output_dir, exist_ok=True)
    for n, order in enumerate(observation.orders):
        if len(order.coordinates.columns):
            try:
                continuum = _fit_continuum(order.coordinates.columns, order.intensity)
                normalized_intensity = order.intensity / continuum
            except Exception as e:
                print(f"\tCould not normalize order #{n}: {e}")
            filename = output_dir / f"{n:02d}.txt"
            with open(filename, "w") as f:
                f.write("#WAVELENGTH\tINTENSITY\n")
                for i, column in enumerate(order.coordinates.columns):
                    f.write(f"{column}\t{normalized_intensity[i]:.10f}\n")
