import argparse
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from services.dataset import Corpuses
from services.jsonio import dump_json
from services.search.strategies import (
    SearchStrategy,
    BaselineSearcher,
    KDTreeSearcher,
    build_searcher,
    get_topk,
)
from services.dto import VectorizedQueryProfile, TopKResult, Profile

logger = logging.getLogger(__name__)


def run_generate_corpus(args: argparse.Namespace) -> int:
    if args.n_profiles < 1:
        raise SystemExit("--n requires an integer >= 1")

    profiles = list(Corpuses.iter_synthetic_profiles(args.n_profiles, seed=args.seed))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / ".rmit" / "dataset" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_json = out_dir / "profiles.json"
    meta_path = out_dir / "metadata.txt"
    payload = dump_json([asdict(p) for p in profiles])
    dataset_json.write_text(payload, encoding="utf-8")
    seed_repr = "null" if args.seed is None else str(args.seed)
    meta_path.write_text(f"N={args.n_profiles}\nseed={seed_repr}\n", encoding="utf-8")
    logger.info(f"Dataset: {dataset_json.resolve()}\nMetadata: {meta_path.resolve()}")
    return 0


def run_search(args: argparse.Namespace) -> int:
    state = 0
    try:
        corpuses: Corpuses = Corpuses.from_json_path(args.dataset)
        vectorized_query: VectorizedQueryProfile = corpuses.build_vectorized_query(args.query_profile)

        benchmark = args.benchmark
        strategy = args.strategy
        if strategy == "baseline":
            searcher_cls: type[SearchStrategy] = BaselineSearcher
        elif strategy == "kdtree":
            searcher_cls = KDTreeSearcher
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")

        build_elapsed: float = 0.0
        searcher: SearchStrategy
        searcher, build_elapsed = build_searcher(searcher_cls, corpuses)
        search_elapsed: float = 0.0
        topk_result: TopKResult
        topk_result, search_elapsed = get_topk(searcher, vectorized_query.vector, vectorized_query.weights, vectorized_query.k)
        profiles: tuple[Profile, ...] = corpuses.get_profiles(topk_result.profile_ids)
        out: dict = {
            "strategy": strategy,
            "profiles": [asdict(p) for p in profiles],
            "distances": topk_result.distances,
        }
        if benchmark:
            out["timing"] = {"search_seconds": search_elapsed, "build_seconds": build_elapsed}
    
        logger.info(f"\n{dump_json(out)}\n")
    except Exception as e:
        logger.error(f"Error: {e}")
        state = 1
    finally:
        return state
