from typing import Any

import numpy as np

from despero.parameters import (MATCHING_LINE_COLUMN_TOLERANCE,
                                MATCHING_LINE_DISTANCE_TOLERANCE)


class Line:
    def __init__(self, order: Any, column: int | float, wavelength: float | None = None):
        self.order = order
        self.column = column
        self.wavelength = wavelength

    def __str__(self):
        return f"{self.column}"

    def get_distance_from(self, other) -> float:
        if self.column >= other.column:
            return self.column - other.column
        else:
            return other.column - self.column


class LinePair:
    def __init__(self, line1: Line, line2: Line):
        self.line1 = line1
        self.line2 = line2
        self.distance = line1.get_distance_from(line2)

    def __str__(self):
        return f"[{self.line1}:{self.line2} ({self.distance})]"

    def get_blue(self):
        if self.line1.column < self.line2.column:
            return self.line1
        if self.line1.column > self.line2.column:
            return self.line2
        raise ValueError("line pair of the same line")

    def get_red(self):
        if self.line1.column < self.line2.column:
            return self.line2
        if self.line1.column > self.line2.column:
            return self.line1
        raise ValueError("line pair of the same line")

    def __eq__(self, other):
        if (
            np.abs(self.get_blue().column - other.get_blue().column) <= MATCHING_LINE_COLUMN_TOLERANCE
            and np.abs(self.get_red().column - other.get_red().column) <= MATCHING_LINE_COLUMN_TOLERANCE
        ):
            return True
        if (
            np.abs(self.get_blue().column - other.get_red().column) <= MATCHING_LINE_COLUMN_TOLERANCE
            and np.abs(self.get_red().column - other.get_blue().column) <= MATCHING_LINE_COLUMN_TOLERANCE
        ):
            return True
        return False

    def matches(self, other) -> bool:
        if self.distance == 0 or other.distance == 0:
            return False
        return np.abs(self.distance - other.distance) <= MATCHING_LINE_DISTANCE_TOLERANCE


class MatchingPair:
    def __init__(self, pair1: LinePair, pair2: LinePair):
        self.pair1 = pair1
        self.pair2 = pair2

    def __str__(self):
        return f"{self.pair1} <-> {self.pair2}"

    def __eq__(self, other):
        if (self.pair1 == other.pair1) and (self.pair2 == other.pair2):
            return True
        if (self.pair1 == other.pair2) and (self.pair2 == other.pair1):
            return True
        return False
