import argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Top-k weighted profile similarity search (stdlib only).",
    )
    subs = p.add_subparsers(dest="command", required=True, help="Available commands")

    gen = subs.add_parser(
        "generate-corpus",
        help="Write N synthetic profiles to .rmit/corpus/YYYYMMDD_HHMMSS/corpus.json (+ metadata).",
    )
    gen.add_argument(
        "--N",
        type=int,
        dest="n_profiles",
        metavar="N",
        required=True,
        help="Number of synthetic profiles (integer ≥ 1).",
    )
    gen.add_argument(
        "--seed", type=int, default=None, help="Optional RNG seed for reproducibility."
    )

    sea = subs.add_parser("search", help="Run weighted top-k similarity search.")
    sea.add_argument("--corpus", required=True, help="Path to JSON corpus array.")
    sea.add_argument("--query", required=True, help="Path to JSON query (reference, weights, k).")
    sea.add_argument(
        "--strategy",
        choices=("baseline", "kdtree", "both"),
        default="baseline",
        help="Search strategy (default: baseline).",
    )
    sea.add_argument(
        "--benchmark",
        action="store_true",
        help="Include perf_counter timings in output / stderr summary.",
    )
    return p
