import argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Top-k weighted profile similarity search (stdlib only).",
    )
    subs = p.add_subparsers(dest="command", required=True, help="Available commands")

    gen = subs.add_parser(
        "build",
        help="Write n synthetic profiles to .rmit/dataset/YYYYMMDD_HHMMSS/profiles.json (+ metadata).",
    )
    gen.add_argument(
        "--n",
        type=int,
        dest="n_profiles",
        metavar="n",
        required=True,
        help="Number of synthetic profiles (integer ≥ 1).",
    )
    gen.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducibility."
    )

    sea = subs.add_parser("search", help="Run weighted top-k similarity search.")
    sea.add_argument("--dataset", required=True, help="Path to JSON dataset (profile array).")
    sea.add_argument(
        "--query-profile",
        required=True,
        dest="query_profile",
        help="Path to JSON query (profile, weights, k).",
    )
    sea.add_argument(
        "--strategy",
        choices=("baseline", "kdtree"),
        default="baseline",
        help="Search strategy (default: baseline).",
    )
    sea.add_argument(
        "--benchmark",
        action="store_true",
        help="Include perf_counter timings in output / stderr summary.",
    )
    return p
