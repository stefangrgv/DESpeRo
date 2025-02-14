from typing import Any


class Order:
    def __init__(self, observation: Any, order_coordinates: list[list[int]]):
        self.observation = observation
        self.order_coordinates = order_coordinates
        self.wavelength = []
        self.intensity = []
        self.normalized_intensity = []
