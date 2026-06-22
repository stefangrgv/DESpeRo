from typing import Any

from despero.store.line import LinePair, MatchingPair


class Order:
    def __init__(self, observation: Any, coordinates: list[list[int]]):
        self.observation = observation
        self.coordinates = coordinates
        self.wavelength = []
        self.intensity = []
        self.normalized_intensity = []
        self.identified_lines = []  # for comp only

    def get_line_pairs(self):
        pairs = []
        for line in self.identified_lines:
            pairs += [LinePair(line, other_line) for other_line in self.identified_lines]
        return pairs

    def match_lines_from(self, other):
        self_pairs = self.get_line_pairs()
        other_pairs = other.get_line_pairs()

        matching_pairs = []
        for self_pair in self_pairs:
            for other_pair in other_pairs:
                if self_pair.matches(other_pair):
                    new_matching_pair = MatchingPair(self_pair, other_pair)
                    append = True
                    for pair_match in matching_pairs:
                        if pair_match == new_matching_pair:
                            append = False
                            break
                    if append:
                        matching_pairs.append(new_matching_pair)
        return matching_pairs
