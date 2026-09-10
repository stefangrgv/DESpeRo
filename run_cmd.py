from pathlib import Path
import argparse

from despero.job import Job


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("observation_dir", type=str)
    parser.add_argument("--cosmic", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bias", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--flat", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--vhelio", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fits-2d", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fits-2d-norm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ascii-2d", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ascii-2d-norm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ascii-1d-norm", action=argparse.BooleanOptionalAction, default=True)

    args = parser.parse_args()
    observation_dir = Path(args.observation_dir)

    if not observation_dir.exists():
        parser.error(f"Observation directory does not exist: {observation_dir}")

    if not observation_dir.is_dir():
        parser.error(f"Observation path is not a directory: {observation_dir}")

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

    job.start()


if __name__ == "__main__":
    main()
