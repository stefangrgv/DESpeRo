from typing import Iterable

import numpy as np
from numpy.polynomial import legendre

from despero.parameters import (ECHELLE_FIT_CLIP_SIGMA, ECHELLE_FIT_DEGREE_COLUMN, ECHELLE_FIT_DEGREE_ORDER,
                                ECHELLE_FIT_MIN_CLIP)

SPEED_OF_LIGHT = 299792.458  # km/s
COLUMN_CENTER = 1024  # columns are scaled to about [-1, 1] with these
COLUMN_HALF_RANGE = 1024


class EchelleSolution:
    """
    Global wavelength solution of an echelle spectrum: wavelength * m = P(column, m),
    where m is the absolute echelle order and P is a 2D Legendre polynomial.
    Orders listed in `offsets` get an extra free zero point (e.g. orders spliced in from another exposure).
    """

    def __init__(
        self,
        coeff: np.ndarray,
        degree_column: int,
        degree_order: int,
        order_range: tuple[int, int],
        offsets: dict[int, float] | None = None,
    ):
        self.coeff = np.asarray(coeff, dtype=np.float64)
        self.degree_column = degree_column
        self.degree_order = degree_order
        self.order_range = (int(order_range[0]), int(order_range[1]))
        self.offsets = {int(m): float(offset) for m, offset in (offsets or {}).items()}

    def _scale_order(self, m: np.ndarray) -> np.ndarray:
        low, high = self.order_range
        half_range = max((high - low) / 2, 1)
        return (m - (low + high) / 2) / half_range

    @staticmethod
    def _design_matrix(
        xs: np.ndarray, ms: np.ndarray, degree_column: int, degree_order: int
    ) -> np.ndarray:
        column_terms = legendre.legvander(xs, degree_column)
        order_terms = legendre.legvander(ms, degree_order)
        return np.einsum("ni,nj->nij", column_terms, order_terms).reshape(len(xs), -1)

    def wavelength(self, columns: Iterable[float], m: int | Iterable[int]) -> np.ndarray:
        columns = np.atleast_1d(np.asarray(columns, dtype=np.float64))
        m = np.broadcast_to(np.asarray(m, dtype=np.float64), columns.shape)
        xs = (columns - COLUMN_CENTER) / COLUMN_HALF_RANGE
        design = self._design_matrix(xs, self._scale_order(m), self.degree_column, self.degree_order)
        wavelength_times_m = design @ self.coeff
        for order, offset in self.offsets.items():
            wavelength_times_m[m == order] += offset
        return wavelength_times_m / m

    @classmethod
    def fit(
        cls,
        columns: Iterable[float],
        orders: Iterable[int],
        wavelengths: Iterable[float],
        degree_column: int,
        degree_order: int,
        clip_sigma: float,
        min_clip: float,
        free_orders: Iterable[int] = (),
        order_range: tuple[int, int] | None = None,
        max_iterations: int = 30,
    ) -> tuple["EchelleSolution", np.ndarray, np.ndarray]:
        """
        Fit the solution to identified lines, iteratively rejecting lines with residuals above
        max(clip_sigma * robust sigma, min_clip) km/s. Returns the solution, the mask of the lines
        that were kept and the residuals of all lines in km/s.
        """
        columns = np.asarray(columns, dtype=np.float64)
        orders = np.asarray(orders, dtype=np.int64)
        wavelengths = np.asarray(wavelengths, dtype=np.float64)
        if order_range is None:
            order_range = (orders.min(), orders.max())
        free_orders = sorted(set(int(m) for m in free_orders) & set(orders.tolist()))
        n_coeff = (degree_column + 1) * (degree_order + 1) + len(free_orders)

        solution = cls(np.zeros((degree_column + 1) * (degree_order + 1)), degree_column, degree_order, order_range)
        xs = (columns - COLUMN_CENTER) / COLUMN_HALF_RANGE
        design = cls._design_matrix(xs, solution._scale_order(orders), degree_column, degree_order)
        design = np.hstack([design, *[(orders == m).astype(np.float64)[:, None] for m in free_orders]])
        target = wavelengths * orders

        keep = np.ones(len(columns), dtype=bool)
        for _ in range(max_iterations):
            if keep.sum() < 2 * n_coeff:
                raise ValueError(f"too few lines for a 2D solution: {keep.sum()} left, {2 * n_coeff} needed")
            coeff, *_ = np.linalg.lstsq(design[keep], target[keep], rcond=None)
            residuals = (target - design @ coeff) / target * SPEED_OF_LIGHT
            sigma = 1.4826 * np.median(np.abs(residuals[keep]))
            new_keep = np.abs(residuals) <= max(clip_sigma * sigma, min_clip)
            if np.array_equal(new_keep, keep):
                break
            keep = new_keep

        n_polynomial = (degree_column + 1) * (degree_order + 1)
        offsets = dict(zip(free_orders, coeff[n_polynomial:]))
        return cls(coeff[:n_polynomial], degree_column, degree_order, order_range, offsets), keep, residuals

    def to_dict(self) -> dict:
        return {
            "coeff": self.coeff.tolist(),
            "degree_column": self.degree_column,
            "degree_order": self.degree_order,
            "order_range": list(self.order_range),
            "offsets": self.offsets,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EchelleSolution":
        return cls(
            data["coeff"], data["degree_column"], data["degree_order"], tuple(data["order_range"]), data["offsets"]
        )


def fit_echelle_solution(
    columns: Iterable[float], orders: Iterable[int], wavelengths: Iterable[float], free_orders: Iterable[int] = ()
) -> tuple[EchelleSolution, np.ndarray, np.ndarray]:
    return EchelleSolution.fit(
        columns,
        orders,
        wavelengths,
        degree_column=ECHELLE_FIT_DEGREE_COLUMN,
        degree_order=ECHELLE_FIT_DEGREE_ORDER,
        clip_sigma=ECHELLE_FIT_CLIP_SIGMA,
        min_clip=ECHELLE_FIT_MIN_CLIP,
        free_orders=free_orders,
    )
