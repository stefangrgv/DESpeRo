from src.parameters import INTENSITY_THRESHOLD


class ApallStore:
    def __init__(self):
        self.apall_image = None
        self.imshow_image = None
        self.threshold = INTENSITY_THRESHOLD
        self.ax = None
        self.fig = None
