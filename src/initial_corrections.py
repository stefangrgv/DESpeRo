from typing import Any

import astroscrappy
import numpy as np


def correct_for_bias(observation: Any, master_bias: Any) -> None:
    target_data = observation.raw_data.astype(np.int64)
    target_data -= master_bias.raw_data
    observation.raw_data = np.clip(target_data, 0, 2**16).astype(np.uint16)


def correct_for_flat(observation: Any, master_flat: Any) -> None:
    corrected_data = observation.raw_data.astype(np.float64) / master_flat.normalized_data
    observation.raw_data = np.clip(corrected_data, 0, 2**16).astype(np.uint16)


def clean_cosmics(stellar: Any) -> None:
    _, clean_data = astroscrappy.detect_cosmics(
        stellar.raw_data,
        sigclip=3.5,  # Detection threshold in sigma
        sigfrac=0.3,  # Fraction of a pixel considered for detection
        objlim=5.0,  # Minimum contrast between cosmic ray and objects
        gain=1.0,  # Gain of the detector (e-/ADU)
        readnoise=stellar.rdnoise,  # Read noise of the detector in electrons
        satlevel=65536,  # Saturation level of the detector in ADU
        niter=10,  # Number of iterations for cleaning
    )
    stellar.raw_data = clean_data
