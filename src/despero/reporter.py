class ReporterBase:
    def render_welcome_screen(self) -> None:
        pass

    def set_status(self, name: str, finished: bool) -> None:
        pass

    def set_master_flats(self, master_flats):
        pass

    def set_flats(self, flats):
        pass

    def set_order_coordinates(self, order_coordinates):
        pass

    def set_comp_standard(self, comp_standard):
        pass

    def set_comp(self, comp):
        pass

    def set_stellar(self, stellar):
        pass

    def warning(self, text):
        pass
