from typing import List

import numpy as np
from numpy.polynomial.chebyshev import Chebyshev, chebval
from scipy.optimize import curve_fit, least_squares

from src.parameters import FIT_WINDOW_HW


def gaussian(x: List[float | int] | np.ndarray, a: float, x0: float, sigma: float, offset: float) -> np.ndarray:
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + offset


def fit_line_with_gaussian(
    col: List[int] | np.ndarray, intensity: List[float | int] | np.ndarray, approx_peak: float
) -> dict:
    col = np.asarray(col)
    intensity = np.asarray(intensity)
    approx_peak_intensity_index = np.argwhere(col == approx_peak)[0][
        0
    ]  # Compensate for cutoff: column number is not equal to index number

    # Find a small window around the approximate peak
    mask = (col > approx_peak - FIT_WINDOW_HW) & (col < approx_peak + FIT_WINDOW_HW)
    col_window = col[mask]
    intensity_window = intensity[mask]

    # Initial guesses for Gaussian parameters
    a_guess = intensity[approx_peak_intensity_index]  # Amplitude
    x0_guess = approx_peak  # Peak
    offset_guess = 0  # Amplitude baseline
    sigma_guess = FIT_WINDOW_HW / 2  # Width
    p0 = [a_guess, x0_guess, sigma_guess, offset_guess]

    # Set bounds for the parameters
    lower_bounds = [0, approx_peak - FIT_WINDOW_HW, 0, 0]  # Amplitude >= 0, x0 within window, sigma >= 0, offset >= 0
    upper_bounds = [
        np.max(intensity),
        approx_peak + FIT_WINDOW_HW,
        np.inf,
        np.percentile(intensity_window, 10),  # Limit the offset to 10% of the intensity in the window
    ]  # No upper limit except for x0 within window
    bounds = lower_bounds, upper_bounds

    # Fit Gaussian to the data
    try:
        popt, pcov = curve_fit(gaussian, col_window, intensity_window, p0=p0, bounds=bounds)
        return {"a": popt[0], "x0": popt[1], "sigma": popt[2], "offset": popt[3], "pcov": pcov}
    except RuntimeError:
        raise RuntimeError("Gaussian fit to line did not converge")


def is_fit_ok(fit_coeffs: List[float]) -> bool:
    errors = np.sqrt(np.diag(fit_coeffs["pcov"]))
    relative_errors = np.asarray(
        [
            errors[0] / fit_coeffs["a"],
            errors[1] / fit_coeffs["x0"],
            errors[2] / fit_coeffs["sigma"],
        ]
    )
    return np.all(relative_errors <= 0.5)


def get_finetuned_chebyshev(
    x: List[float] | np.ndarray, y: List[float] | np.ndarray, initial_coeffs: List[float]
) -> np.ndarray:
    def residuals(coeffs, x_new, y_new, lambda_reg=0.1):
        # Compute the difference between the new dataset and the adjusted model
        model_vals = chebval(x_new, coeffs)
        data_residuals = model_vals - y_new
        # Regularization term: Penalize large deviations from the original fit
        reg_residuals = lambda_reg * (coeffs - initial_coeffs)

        return np.concatenate([data_residuals, reg_residuals])

    result = least_squares(residuals, initial_coeffs, args=(x, y))
    return Chebyshev(result.x)
