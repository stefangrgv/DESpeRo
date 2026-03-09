from typing import Any


class Order:
    def __init__(self, observation: Any, coordinates: list[list[int]]):
        self.observation = observation
        self.coordinates = coordinates
        self.wavelength = []
        self.intensity = []
        self.normalized_intensity = []
