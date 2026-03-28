from despero.store.master_flat import MasterFlat
from despero.store.observation import Observation
from despero.store.order_coordinates import OrderCoordinates


class ReporterBase:
    def render_welcome_screen(self) -> None:
        pass

    def set_status(self, name: str, finished: bool) -> None:
        pass

    def set_master_flats(self, master_flats: list[MasterFlat]):
        pass

    def set_flats(self, flats: list[Observation]):
        pass

    def set_order_coordinates(self, order_coordinates: list[OrderCoordinates]):
        pass

    def set_comp_standard(self, comp_standard: Observation):
        pass

    def set_comp(self, comps: list[Observation]):
        pass

    def set_stellar(self, stellar: Observation):
        pass

    def warning(self, text: str):
        pass

    def set_files_progress(
        self, all: list[Observation] | None = None, file: Observation | None = None, done: bool = False
    ):
        pass
