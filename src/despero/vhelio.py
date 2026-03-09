from typing import Any

from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time


def _remove_doppler_shift(wl: float, rv: float) -> float:
    return wl + wl * (rv / 299792.458)


def correct_vhelio(observation: Any):
    # Rozhen NAO coordinates
    latitude = 41.6925
    longitude = 24.738055
    altitude = 1759
    rozhen = EarthLocation.from_geodetic(longitude, latitude, altitude)

    target = SkyCoord(observation.ra, observation.dec, unit=(u.hourangle, u.deg))
    jd = Time(observation.jd, format="jd")
    observation.vhelio = target.radial_velocity_correction(obstime=jd, location=rozhen).to("km/s").value
    for i in range(len(observation.orders)):
        observation.orders[i].wavelength = _remove_doppler_shift(observation.orders[i].wavelength, observation.vhelio)
