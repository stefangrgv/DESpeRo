import os
from typing import Any


def save_as_ascii(observation: Any) -> None:
    output_dir = "ascii_spectra"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    with open(f"{output_dir}/{output_filename}.txt", "w") as f:
        f.write("#WAVELENGTH\tINTENSITY\n")
        for order in observation.orders:
            for i in range(len(order.wavelength)):
                f.write(f"{order.wavelength[i]:.4f}\t{int(order.intensity[i])}\n")

    print(f"Saved 2d/{output_filename}")
