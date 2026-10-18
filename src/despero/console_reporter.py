import sys
import time
from typing import Any, TextIO

from despero.reporter import ReporterBase

STEP_LABELS = {
    "cosmics": "Clean cosmics",
    "bias": "Correct for bias",
    "orders": "Trace echelle orders",
    "flat": "Correct for flat",
    "spectra": "Extract spectra",
    "wavelength": "Calibrate for wavelength",
    "normalize": "Normalize spectra",
    "stitch": "Stitch spectra",
    "save": "Save files",
}

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, seconds = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class ConsoleReporter(ReporterBase):
    """Reports Job progress and warnings to a terminal, one line per finished step."""

    def __init__(self, stream: TextIO | None = None, log: TextIO | None = None, live: bool = True):
        self.stream = stream or sys.stdout
        self.log = log  # also receives every reported line, without colors
        self.is_tty = self.stream.isatty()
        self.live = live and self.is_tty  # redraw a progress line for the running step
        self.warnings = []
        self._step = None
        self._step_start = 0.0
        self._files_total = 0
        self._files_done = 0
        self._line_open = False

    def color(self, text: str, color: str) -> str:
        return f"{color}{text}{RESET}" if self.is_tty else text

    def print(self, text: str, plain: str | None = None) -> None:
        self._clear_line()
        self.stream.write(text + "\n")
        self.stream.flush()
        if self.log:
            self.log.write((plain if plain is not None else text) + "\n")
            self.log.flush()
        self._draw_progress()

    def _clear_line(self) -> None:
        if self._line_open:
            self.stream.write("\r\033[K")
            self._line_open = False

    def _draw_progress(self) -> None:
        if not self.live or self._step is None:
            return
        text = f"  … {STEP_LABELS.get(self._step, self._step)}"
        if self._files_total:
            text += f"  {self._files_done}/{self._files_total} files"
        self.stream.write("\r\033[K" + self.color(text, DIM))
        self.stream.flush()
        self._line_open = True

    def render_working_screen(self) -> None:
        pass

    def export_raw_data(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_finished(self) -> None:
        self._clear_line()

    def set_status(self, name: str, finished: bool) -> None:
        if not finished:
            self._step = name
            self._step_start = time.monotonic()
            self._draw_progress()
            return
        if name != self._step:  # Job also reports skipped steps as finished
            return
        elapsed = format_duration(time.monotonic() - self._step_start)
        files = f", {self._files_done}/{self._files_total} files" if self._files_done else ""
        self._step = None
        self._files_total = self._files_done = 0
        line = f"  ✓ {STEP_LABELS.get(name, name)} ({elapsed}{files})"
        self.print(self.color(line, GREEN), plain=line)

    def set_files_progress(self, all: list | None = None, file: Any | None = None, done: bool = False) -> None:
        if all is not None:
            self._files_total = len(all)
            self._files_done = 0
        if file is not None and done:
            self._files_done += 1
        self._draw_progress()

    def warning(self, text: str) -> None:
        self.warnings.append(text)
        line = f"  ! {text}"
        self.print(self.color(line, YELLOW), plain=line)
