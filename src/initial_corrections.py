from typing import Any

import astroscrappy
import numpy as np


def correct_for_bias(store: Any) -> None:
    print("Correcting for bias...")
    target_observations = [*store.flat, *store.comp, *store.stellar]
    for master_bias in store.master_biases:
        observations = [
            observation for observation in target_observations if observation.readtime == master_bias.readtime
        ]
        for observation in observations:
            target_data = observation.raw_data.astype(np.int32)
            target_data -= master_bias.raw_data
            observation.raw_data = np.clip(target_data, 0, 2**16).astype(np.uint16)


def correct_for_flat(store: Any) -> None:
    target_observations = [*store.comp, *store.stellar]
    print("Correcting for flat...")
    for master_flat in store.master_flats:
        observations = [
            observation for observation in target_observations if observation.readtime == master_flat.readtime
        ]
        master_flat_float64 = master_flat.raw_data.astype(np.float64)
        normalized_master_flat = master_flat_float64 / np.max(master_flat_float64)
        for observation in observations:
            corrected_data = observation.raw_data.astype(np.float64) / normalized_master_flat
            observation.raw_data = np.clip(corrected_data, 0, 2**16).astype(np.uint16)


def _remove_doppler_shift(wl: int | float, rv: int | float) -> float:
    return wl + wl * (rv / 299792.458)


def correct_for_vhelio(store: Any) -> None:
    print("Correcting for heliocentric velocity...")
    for stellar in store.stellar:
        if stellar.vhelio is not None:
            for i in range(len(stellar.orders)):
                stellar.orders[i].wavelength = _remove_doppler_shift(stellar.orders[i].wavelength, stellar.vhelio)


def clean_cosmics(store: Any) -> None:
    for spectrum in [*store.comp, *store.stellar]:
        print(f"Cleaning cosmics from {spectrum.fits_file}...")
        _, clean_data = astroscrappy.detect_cosmics(
            spectrum.raw_data,
            sigclip=3.5,  # Detection threshold in sigma
            sigfrac=0.3,  # Fraction of a pixel considered for detection
            objlim=5.0,  # Minimum contrast between cosmic ray and objects
            gain=1.0,  # Gain of the detector (e-/ADU)
            readnoise=spectrum.rdnoise,  # Read noise of the detector in electrons
            satlevel=65536,  # Saturation level of the detector in ADU
            niter=10,  # Number of iterations for cleaning
        )
        spectrum.raw_data = clean_data
