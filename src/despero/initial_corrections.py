from typing import Any

import astroscrappy
import numpy as np


def correct_for_bias(observation: Any, master_bias: Any) -> None:
    target_data = observation.raw_data.astype(np.int64)
    target_data -= master_bias.raw_data
    observation.raw_data = np.clip(target_data, 0, 2**16).astype(np.uint16)


def correct_for_flat(observation: Any, master_flat: Any) -> None:
    # import matplotlib.pyplot as plt
    # from despero.parameters import APERTURE_HEIGHT
    # fig, ax = plt.subplots(ncols=2, sharex=True, sharey=True)
    # ax[0].imshow(observation.raw_data, cmap="gray")
    # ax[1].imshow(master_flat.normalized_data, cmap="gray")
    # for coordinates in [observation.store.order_coordinates[25], observation.store.order_coordinates[47]]:
    #     for i in range(len(coordinates.columns)):
    #         column = coordinates.columns[i]
    #         row = coordinates.rows[i]
    #         for n in [0, 1]:
    #             ax[n].plot(
    #                 [column, column],
    #                 [row - (APERTURE_HEIGHT - 1), row + (APERTURE_HEIGHT - 1)],
    #                 color="lime",
    #                 alpha=0.075,
    #                 lw=3,
    #             )
    # plt.show()
    # import pdb; pdb.set_trace()
    # corrected_data = observation.raw_data.astype(np.float64) / master_flat.normalized_data
    # observation.raw_data = np.clip(corrected_data, 0, 2**16).astype(np.uint16)
    observation.raw_data = observation.raw_data / master_flat.normalized_data


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
