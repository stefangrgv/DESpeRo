import argparse
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path

from despero.console_reporter import RED, ConsoleReporter, format_duration
from despero.job import Job

LOG_FILE_NAME = "despero.log"


@dataclass
class NightResult:
    name: str
    elapsed: float = 0.0
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    output_dir: Path | None = None
    log_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def add_job_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("reduction steps and outputs")
    flag = argparse.BooleanOptionalAction
    group.add_argument("--cosmic", action=flag, default=True, help="clean cosmic rays (default: on)")
    group.add_argument("--bias", action=flag, default=True, help="correct for bias (default: on)")
    group.add_argument("--flat", action=flag, default=False, help="correct for flat (default: off)")
    group.add_argument("--vhelio", action=flag, default=True, help="apply heliocentric correction (default: on)")
    group.add_argument("--fits-2d", action=flag, default=True, help="save 2D FITS (default: on)")
    group.add_argument("--fits-2d-norm", action=flag, default=True, help="save normalized 2D FITS (default: on)")
    group.add_argument("--ascii-2d", action=flag, default=True, help="save 2D ASCII (default: on)")
    group.add_argument("--ascii-2d-norm", action=flag, default=True, help="save normalized 2D ASCII (default: on)")
    group.add_argument("--ascii-1d-norm", action=flag, default=True, help="save normalized 1D ASCII (default: on)")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help=f"also show the pipeline's own output (always saved to {LOG_FILE_NAME})"
    )


def run_night(observation_dir: Path, args: argparse.Namespace) -> NightResult:
    """Reduce one night, report progress on the terminal and write the full output to a log file."""
    result = NightResult(name=observation_dir.name)
    terminal = sys.stdout
    start = time.monotonic()
    job = Job(
        observation_dir=observation_dir,
        cmd_path=Path.cwd(),
        cosmic=args.cosmic,
        bias=args.bias,
        flat=args.flat,
        vhelio=args.vhelio,
        fits_2d=args.fits_2d,
        fits_2d_norm=args.fits_2d_norm,
        ascii_2d=args.ascii_2d,
        ascii_2d_norm=args.ascii_2d_norm,
        ascii_1d_norm=args.ascii_1d_norm,
    )
    result.output_dir = job.store.output_directory
    result.log_path = result.output_dir / LOG_FILE_NAME

    with open(result.log_path, "w") as log:
        reporter = ConsoleReporter(stream=terminal, log=log, live=not args.verbose)
        output = _Tee(log, terminal) if args.verbose else log
        try:
            with redirect_stdout(output), redirect_stderr(output):
                job.start(reporter=reporter)
        except (Exception, SystemExit) as exc:
            log.write(traceback.format_exc())
            reporter.set_finished()
            result.error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            reporter.print(reporter.color(f"  ✗ {result.error}", RED), plain=f"  ✗ {result.error}")
        finally:
            result.warnings = reporter.warnings
            result.elapsed = time.monotonic() - start
    return result


def describe(result: NightResult) -> str:
    if not result.ok:
        return f"failed after {format_duration(result.elapsed)}, see {result.log_path}"
    warnings = len(result.warnings)
    issues = f", {warnings} warning{'s' if warnings != 1 else ''}" if warnings else ""
    return f"done in {format_duration(result.elapsed)}{issues} → {result.output_dir}"


def main():
    parser = argparse.ArgumentParser(description="Reduce one night of echelle observations with DESpeRo.")
    parser.add_argument("observation_dir", type=Path, help="directory with the FITS files and Journal.txt")
    add_job_arguments(parser)
    args = parser.parse_args()

    if not args.observation_dir.is_dir():
        parser.error(f"not a directory: {args.observation_dir}")
    if not (args.observation_dir / "Journal.txt").is_file():
        parser.error(f"no Journal.txt in {args.observation_dir}")

    print(f"Reducing {args.observation_dir}")
    result = run_night(args.observation_dir, args)
    print(describe(result))
    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
