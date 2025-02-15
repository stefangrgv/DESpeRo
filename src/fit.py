import numpy as np
from scipy.optimize import curve_fit


def gaussian(x: list | np.ndarray, a: float, x0: float, sigma: float, offset: float) -> np.ndarray:
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + offset


def fit_line_with_gaussian(col: list | np.ndarray, intensity: list | np.ndarray, approx_peak: float) -> dict:
    col = np.asarray(col)
    intensity = np.asarray(intensity)
    approx_peak_intensity_index = np.argwhere(col == approx_peak)[0][
        0
    ]  # Compensate for cutoff: column number is not equal to index number

    # Find a small window around the approximate peak
    window_size = 5
    mask = (col > approx_peak - window_size) & (col < approx_peak + window_size)
    col_window = col[mask]
    intensity_window = intensity[mask]

    # Initial guesses for Gaussian parameters
    a_guess = intensity[approx_peak_intensity_index]  # Amplitude
    x0_guess = approx_peak  # Peak
    offset_guess = 0  # Amplitude baseline
    sigma_guess = window_size / 2  # Width
    p0 = [a_guess, x0_guess, sigma_guess, offset_guess]

    # Set bounds for the parameters
    lower_bounds = [0, approx_peak - window_size, 0, 0]  # Amplitude >= 0, x0 within window, sigma >= 0, offset >= 0
    upper_bounds = [
        np.max(intensity),
        approx_peak + window_size,
        np.inf,
        0.01,
    ]  # No upper limit except for x0 within window
    bounds = lower_bounds, upper_bounds

    # Fit Gaussian to the data
    try:
        popt, _ = curve_fit(gaussian, col_window, intensity_window, p0=p0, bounds=bounds)
        return {"a": popt[0], "x0": popt[1], "sigma": popt[2], "offset": popt[3]}
    except RuntimeError:
        raise RuntimeError("Gaussian fit to line did not converge")
