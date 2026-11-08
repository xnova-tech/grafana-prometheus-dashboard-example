"""Send one deterministic traffic profile to the demo API."""

import argparse

import httpx

from grafana_demo.traffic import LoadConfig, LoadFailure, Profile, run_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=tuple(Profile), required=True)
    parser.add_argument("--seconds", type=int, default=75)
    parser.add_argument("--rate", type=int, default=6, help="Target requests per second")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        config = LoadConfig(
            profile=Profile(args.mode),
            seconds=args.seconds,
            requests_per_second=args.rate,
            base_url=args.url,
        )
        with httpx.Client(base_url=config.base_url, timeout=5.0) as client:
            result = run_profile(config, client)
    except (LoadFailure, ValueError) as error:
        raise SystemExit(f"load failed: {error}") from error
    print(result.render())


if __name__ == "__main__":
    main()
