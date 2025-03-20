import os
from typing import Any


def save_as_1d_ascii(observation: Any) -> None:
    output_dir = os.path.join("ascii_spectra", "1d")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    with open(f"{output_dir}/{output_filename}.txt", "w") as f:
        f.write("#WAVELENGTH\tINTENSITY\n")
        for order in observation.orders:
            for i in range(len(order.wavelength)):
                f.write(f"{order.wavelength[i]:.4f}\t{int(order.intensity[i])}\n")

    print(f"Saved {output_dir}/{output_filename}")


def save_as_2d_ascii(observation: Any) -> None:
    output_dir = os.path.join("ascii_spectra", "2d")
    os.makedirs(output_dir, exist_ok=True)
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    for n, order in enumerate(observation.orders):
        output_filename = f"{output_filename_base}_{n + 1}"
        with open(f"{output_dir}/{output_filename}.txt", "w") as f:
            f.write("#WAVELENGTH\tINTENSITY\n")
            for i in range(len(order.wavelength)):
                f.write(f"{order.wavelength[i]:.4f}\t{int(order.intensity[i])}\n")

    print(f"Saved {output_dir}/{output_filename_base}")
