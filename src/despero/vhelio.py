from typing import Any, List

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time


def _remove_doppler_shift(wl: List[float], rv: float) -> float:
    wl = np.asarray(wl)
    return wl + wl * (rv / 299792.458)


def correct_vhelio(observation: Any):
    # Rozhen NAO coordinates
    latitude = 41.6925
    longitude = 24.738055
    altitude = 1759
    rozhen = EarthLocation.from_geodetic(longitude, latitude, altitude)

    if observation.jd is None:
        raise ValueError("no usable JD-OBS")

    target = SkyCoord(observation.ra, observation.dec, unit=(u.hourangle, u.deg))
    jd = Time(observation.jd, format="jd")
    observation.vhelio = target.radial_velocity_correction(obstime=jd, location=rozhen).to("km/s").value
    observation.header["VHELIO"] = (observation.vhelio, "applied heliocentric correction (km/s)")
    observation.header["VHJD"] = (observation.jd, "JD used for the VHELIO correction")
    for i in range(len(observation.orders)):
        observation.orders[i].wavelength = _remove_doppler_shift(observation.orders[i].wavelength, observation.vhelio)
