from typing import Any

from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time


def _remove_doppler_shift(wl: float, rv: float) -> float:
    return wl + wl * (rv / 299792.458)


def correct_vhelio(store: Any):
    print("Correcting for heliocentric velocity...")

    # Rozhen NAO coordinates
    latitude = 41.6925
    longitude = 24.738055
    altitude = 1759
    rozhen = EarthLocation.from_geodetic(longitude, latitude, altitude)

    for stellar in store.stellar:
        target = SkyCoord(stellar.ra, stellar.dec, unit=(u.hourangle, u.deg))
        jd = Time(stellar.jd, format="jd")
        stellar.vhelio = target.radial_velocity_correction(obstime=jd, location=rozhen).to("km/s").value
        for i in range(len(stellar.orders)):
            stellar.orders[i].wavelength = _remove_doppler_shift(stellar.orders[i].wavelength, stellar.vhelio)
