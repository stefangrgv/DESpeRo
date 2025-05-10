import os
from pathlib import Path
from typing import Any


def save_as_1d_ascii_norm(observation: Any) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "1d"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/{output_filename_base}.txt", "w") as f:
        f.write("#WAVELENGTH\tINTENSITY\n")
        for i in range(len(observation.oned_wavelength)):
            f.write(f"{observation.oned_wavelength[i]:.10f}\t{observation.oned_intensity[i]:.10f}\n")

    print(f"\tSaved {output_dir}/{output_filename_base}")


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
        output_filename = f"{output_filename_base}_{n + 1}"
        with open(f"{output_dir}/{output_filename}.txt", "w") as f:
            if normalized:
                f.write("#WAVELENGTH\tNORMALIZED INTENSITY\n")
                for i in range(len(order.wavelength)):
                    f.write(f"{order.wavelength[i]:.10f}\t{order.normalized_intensity[i]:.10f}\n")
            else:
                f.write("#WAVELENGTH\tINTENSITY\n")
                for i in range(len(order.wavelength)):
                    f.write(f"{order.wavelength[i]:.10f}\t{order.intensity[i]:.10f}\n")

    print(f"\tSaved {output_dir}")
