import argparse
import logging
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from services.dataset import Corpuses
from services.helper import hits_equal
from services.jsonio import dump_json
from services.search.benchmark import timed_search, timed_searcher_construct
from services.search.strategies.base import SearchStrategy
from services.search.strategies.baseline import BaselineSearcher
from services.search.strategies.kdtree import KDTreeSearcher

logger = logging.getLogger(__name__)


def _run_single_strategy_search(
    corpuses: Corpuses,
    query_vec: tuple[float, float, float, float, float],
    weights: tuple[float, float, float, float, float],
    k: int,
    benchmark: bool,
    strategy: str,
) -> dict:
    if strategy == "baseline":
        searcher_cls: type[SearchStrategy] = BaselineSearcher
    elif strategy == "kdtree":
        searcher_cls = KDTreeSearcher
    else:
        raise ValueError(f"unknown strategy: {strategy!r}")

    build_elapsed = 0.0
    if benchmark:
        searcher, build_elapsed = timed_searcher_construct(searcher_cls, corpuses)
    else:
        searcher = searcher_cls(corpuses)
    hits, search_elapsed = (
        timed_search(searcher, query_vec, weights, k)
        if benchmark
        else (searcher.search(query_vec, weights, k), 0.0)
    )
    out: dict = {
        "strategy": strategy,
        "hits": [{"profile_id": h[0], "distance": h[1]} for h in hits],
    }
    if benchmark:
        out["timing"] = {"search_seconds": search_elapsed, "build_seconds": build_elapsed}

    return out


def _run_both_strategies_search(
    corpuses: Corpuses,
    query_vec: tuple[float, float, float, float, float],
    weights: tuple[float, float, float, float, float],
    k: int,
) -> dict:
    b_build = k_build = 0.0

    base, b_build = timed_searcher_construct(BaselineSearcher, corpuses)
    tree, k_build = timed_searcher_construct(KDTreeSearcher, corpuses)

    b_hits, b_search = timed_search(base, query_vec, weights, k)
    k_hits, k_search = timed_search(tree, query_vec, weights, k)

    if not hits_equal(b_hits, k_hits):
        logger.error("Equivalence check FAILED: baseline vs kdtree differ")
        logger.error("baseline: %s", b_hits)
        logger.error("kdtree: %s", k_hits)
        raise ValueError("Equivalence check FAILED: baseline vs kdtree differ")

    out: dict = {
        "strategy": "both_match",
        "hits": [{"profile_id": h[0], "distance": h[1]} for h in b_hits],
        "timing": {
            "baseline_build_seconds": b_build,
            "baseline_search_seconds": b_search,
            "kdtree_build_seconds": k_build,
            "kdtree_search_seconds": k_search,
        },
    }
    return out


def run_generate_corpus(args: argparse.Namespace) -> int:
    if args.n_profiles < 1:
        raise SystemExit("--N requires an integer >= 1")

    profiles = list(Corpuses.iter_synthetic_profiles(args.n_profiles, seed=args.seed))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / ".rmit" / "corpus" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = out_dir / "corpus.json"
    meta_path = out_dir / "metadata.txt"
    payload = dump_json([asdict(p) for p in profiles])
    corpus_path.write_text(payload, encoding="utf-8")
    seed_repr = "null" if args.seed is None else str(args.seed)
    meta_path.write_text(f"N={args.n_profiles}\nseed={seed_repr}\n", encoding="utf-8")
    logger.info(f"Corpus: {corpus_path.resolve()}\nMetadata: {meta_path.resolve()}")
    return 0


def run_search(args: argparse.Namespace) -> int:
    state = 0
    try:
        corpuses = Corpuses.from_json_path(args.corpus)
        query_vec, weights, k = corpuses.load_query(args.query)

        benchmark = args.benchmark
        strategy = args.strategy
        if strategy in ("baseline", "kdtree"):
            out = _run_single_strategy_search(corpuses, query_vec, weights, k, benchmark, strategy)
            logger.info(f"\n{dump_json(out)}\n")
        else:
            out = _run_both_strategies_search(corpuses, query_vec, weights, k)
            logger.info(f"\n{dump_json(out)}\n")
            n = len(corpuses.normalized_profiles)
            k_search = out["timing"]["kdtree_search_seconds"]
            k_build = out["timing"]["kdtree_build_seconds"]
            b_search = out["timing"]["baseline_search_seconds"]
            b_build = out["timing"]["baseline_build_seconds"]
            if k_search > 0.0:
                speedup = b_search / k_search
                summary = (
                    f"\n[benchmark] corpus_size={n} k={k}\n"
                    f"  Baseline: O(n) full scan — build {b_build:.6f}s, search {b_search:.6f}s\n"
                    f"  KD-tree:  O(n log n) build typical; O(log n) average-case query vs O(n) scan — "
                    f"build {k_build:.6f}s, search {k_search:.6f}s\n"
                    f"  Search speedup (baseline_time / kdtree_time): {speedup:.2f}x\n"
                )
            else:
                summary = (
                    f"\n[benchmark] corpus_size={n} k={k}\n  KD-tree search time rounded to zero.\n"
                )
            logger.info(summary)
    except Exception as e:
        logger.error(f"Error: {e}")
        state = 1
    finally:
        return state
