import os
from pathlib import Path
from typing import Any

from astropy.io import fits
from astropy.wcs import WCS


def save_as_fits(observation: Any, normalized: bool = False) -> None:
    output_dir = Path(os.path.dirname(observation.fits_file))
    output_filename_base = os.path.basename(observation.fits_file.replace(".fits", "").replace(".FITS", ""))
    output_dir = output_dir / "reduced" / "2d" / "fits"
    if normalized:
        output_dir = output_dir / "normalized" / output_filename_base
    else:
        output_dir = output_dir / output_filename_base

    os.makedirs(output_dir, exist_ok=True)

    for i in range(len(observation.orders)):
        try:
            if normalized:
                flux_array = observation.orders[i].normalized_intensity
            else:
                flux_array = observation.orders[i].intensity
            wavelength = observation.orders[i].wavelength
            cheb_coefs = observation.orders[i].coordinates.coeff.tolist()

            hdu = fits.PrimaryHDU(data=flux_array)
            hdr = hdu.header

            hdr["NAXIS"] = 1
            hdr["NAXIS1"] = len(flux_array)

            hdr["BUNIT"] = ""

            w = WCS(naxis=1)
            w.wcs.ctype = ["AWAV"]
            w.wcs.crpix = [1]
            w.wcs.crval = [wavelength[0]]

            # Compute a nominal increment (assumes nearly uniform spacing)
            if len(wavelength) > 1:
                dw = wavelength[1] - wavelength[0]
            else:
                dw = 1.0
            w.wcs.cdelt = [dw]
            hdr.update(w.to_header())
            hdr["WAT1_001"] = "system=multispec label=Wavelength units=Angstroms"
            order = len(cheb_coefs) - 1
            coeff_str = " ".join(f"coeff{i}={coef:.6g}" for i, coef in enumerate(cheb_coefs))
            hdr["WAT2_001"] = f"wtype=chebyshev order={order} {coeff_str}"
            hdu.writeto(f"{output_dir}/{output_filename_base}_order_{i + 1}.fits", overwrite=True)
        except Exception as exc:
            print(f"Error: cannot save .fits spectrum for order #{i + 1} of {observation.fits_file}: {exc}")
        # print(f"\tSaved {output_dir}/{output_filename_base}")
