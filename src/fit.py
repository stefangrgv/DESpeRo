import numpy as np
from scipy.optimize import curve_fit


def gaussian(x, a, x0, sigma, offset):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + offset


def find_line_peak(x, y, approx_peak):
    x = np.asarray(x)
    y = np.asarray(y)
    # Find a small window around the approximate peak
    window_size = 5  # Adjust based on expected peak width
    mask = (x > approx_peak - window_size) & (x < approx_peak + window_size)
    x_window = x[mask]
    y_window = y[mask]

    # Initial guesses for Gaussian parameters
    a_guess = y[approx_peak]  # Amplitude
    x0_guess = approx_peak  # Center
    offset_guess = 0  # Baseline
    sigma_guess = window_size / 2  # Width
    p0 = [a_guess, x0_guess, sigma_guess, offset_guess]

    # Set bounds for the parameters
    lower_bounds = [0, approx_peak - window_size, 0, 0]  # Amplitude >= 0, x0 within window, sigma >= 0, offset >= 0
    upper_bounds = [np.max(y), approx_peak + window_size, np.inf, 0.01]  # No upper limit except for x0 within window
    bounds = lower_bounds, upper_bounds

    # Fit Gaussian to the data
    try:
        popt, _ = curve_fit(gaussian, x_window, y_window, p0=p0, bounds=bounds)
        return {"a": popt[0], "x0": popt[1], "sigma": popt[2], "offset": popt[3]}
    except RuntimeError:
        raise RuntimeError("Gaussian fit to line did not converge")
