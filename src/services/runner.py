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


def run_generate_corpus(n_profiles: int, seed: int | None = None) -> int:
    if n_profiles < 1:
        raise SystemExit("--n requires an integer >= 1")

    profiles = list(Corpuses.iter_synthetic_profiles(n_profiles, seed=seed))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / ".rmit" / "dataset" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_json = out_dir / "profiles.json"
    meta_path = out_dir / "metadata.txt"
    payload = dump_json([asdict(p) for p in profiles])
    dataset_json.write_text(payload, encoding="utf-8")
    seed_repr = "null" if seed is None else str(seed)
    meta_path.write_text(f"N={n_profiles}\nseed={seed_repr}\n", encoding="utf-8")
    logger.info(f"Dataset: {dataset_json.resolve()}\nMetadata: {meta_path.resolve()}")
    return 0


def run_search(
    dataset: str | Path,
    query_profile: str | Path,
    strategy: str,
    benchmark: bool = False,
) -> int:
    state = 0
    try:
        corpuses: Corpuses = Corpuses.from_json_path(dataset)
        vectorized_query: VectorizedQueryProfile = corpuses.build_vectorized_query(query_profile)

        if strategy == "baseline":
            searcher_cls: type[SearchStrategy] = BaselineSearcher
        elif strategy == "kdtree":
            searcher_cls = KDTreeSearcher
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")

        searcher: SearchStrategy
        searcher, build_elapsed = build_searcher(searcher_cls, corpuses)
        topk_result: TopKResult
        topk_result, search_elapsed = get_topk(
            searcher, vectorized_query.vector, vectorized_query.weights, vectorized_query.k
        )
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
