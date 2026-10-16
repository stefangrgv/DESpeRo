"""Reduce every observation night (a subdirectory with a Journal.txt) inside a root directory."""

import argparse
import sys
import time
from pathlib import Path

from despero.console_reporter import GREEN, RED, YELLOW, format_duration
from run_cmd import LOG_FILE_NAME, NightResult, add_job_arguments, describe, run_night


def find_nights(root_dir: Path) -> tuple[list[Path], list[Path]]:
    subdirs = sorted(d for d in root_dir.iterdir() if d.is_dir())
    nights = [d for d in subdirs if (d / "Journal.txt").is_file()]
    others = [d for d in subdirs if d not in nights]
    return nights, others


def has_output(night: Path) -> bool:
    output_dir = Path.cwd() / "reduced" / night.name
    return output_dir.is_dir() and any(f.name != LOG_FILE_NAME for f in output_dir.iterdir())


def paint(text: str, color: str) -> str:
    return f"{color}{text}\033[0m" if sys.stdout.isatty() else text


def print_summary(results: list[NightResult], not_run: list[Path], total_elapsed: float) -> None:
    if not results and not not_run:
        return
    width = max(len(r.name) for r in results) if results else 5
    width = max([width, 5, *(len(n.name) for n in not_run)])
    print(f"\nSummary ({format_duration(total_elapsed)})")
    for r in results:
        if not r.ok:
            error = r.error if len(r.error) <= 70 else r.error[:69] + "…"
            status = paint("FAILED", RED) + f"   {error}"
        elif r.warnings:
            status = paint(f"{len(r.warnings)} warning{'s' if len(r.warnings) != 1 else ''}", YELLOW)
        else:
            status = paint("ok", GREEN)
        print(f"  {r.name:<{width}}  {format_duration(r.elapsed):>8}  {status}")
    for night in not_run:
        print(f"  {night.name:<{width}}  {'':>8}  not run")

    failed = [r for r in results if not r.ok]
    warned = [r for r in results if r.ok and r.warnings]
    parts = [f"{len(results) - len(failed) - len(warned)} ok"]
    if warned:
        parts.append(f"{len(warned)} with warnings")
    if failed:
        parts.append(f"{len(failed)} failed")
    if not_run:
        parts.append(f"{len(not_run)} not run")
    print(", ".join(parts))
    if failed or warned:
        print(f"Details are in each night's {LOG_FILE_NAME}.")


def main():
    parser = argparse.ArgumentParser(
        description="Reduce every observation night inside ROOT_DIR with DESpeRo, one after another. "
        "A night is a subdirectory with a Journal.txt; results go to ./reduced/<night>.",
    )
    parser.add_argument("root_dir", type=Path, help="directory that contains one subdirectory per night")
    parser.add_argument("--only", nargs="+", metavar="NIGHT", help="reduce only these nights (subdirectory names)")
    parser.add_argument("--skip-done", action="store_true", help="skip nights that already have output in ./reduced")
    parser.add_argument("--dry-run", action="store_true", help="list the nights that would be reduced and exit")
    add_job_arguments(parser)
    args = parser.parse_args()

    if not args.root_dir.is_dir():
        parser.error(f"not a directory: {args.root_dir}")

    nights, others = find_nights(args.root_dir)
    if args.only:
        unknown = sorted(set(args.only) - {n.name for n in nights})
        if unknown:
            parser.error(f"no such night (or no Journal.txt): {', '.join(unknown)}")
        nights = [n for n in nights if n.name in args.only]
    done = [n for n in nights if args.skip_done and has_output(n)]
    nights = [n for n in nights if n not in done]

    print(f"{len(nights)} night{'s' if len(nights) != 1 else ''} to reduce in {args.root_dir.resolve()}")
    print(f"Output: {Path.cwd() / 'reduced'}")
    if others:
        print(f"Ignoring {len(others)} director{'ies' if len(others) != 1 else 'y'} without Journal.txt: "
              + ", ".join(d.name for d in others))
    if done:
        print(f"Skipping {len(done)} already reduced: " + ", ".join(d.name for d in done))
    if args.dry_run:
        for night in nights:
            print(f"  {night.name}")
        return
    if not nights:
        return

    results: list[NightResult] = []
    start = time.monotonic()
    interrupted = False
    for i, night in enumerate(nights, start=1):
        print(f"\n[{i}/{len(nights)}] {night.name}")
        try:
            result = run_night(night, args)
        except KeyboardInterrupt:
            interrupted = True
            print(paint("\nInterrupted.", RED))
            break
        results.append(result)
        print(f"  {describe(result)}")

    print_summary(results, nights[len(results):], time.monotonic() - start)
    if interrupted:
        sys.exit(130)
    sys.exit(0 if all(r.ok for r in results) else 1)


if __name__ == "__main__":
    main()
