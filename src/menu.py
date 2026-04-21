"""Interactive CLI menu for the Top-K Profile Similarity Search tool."""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import pickle
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from services.dataset import Corpuses
from services.jsonio import dump_json
from services.runner import run_generate_corpus, run_search
from services.search.strategies import KDTreeSearcher, get_topk  # noqa: F401

logger = logging.getLogger(__name__)

_DATASET_ROOT = Path(".rmit/dataset")
_MENU = """
========================================
  Top-K Profile Similarity Search
========================================
1. Generate dataset (100,000 profiles)
2. Search with Baseline strategy
3. Search with KD-tree strategy
4. Benchmark: Baseline vs KD-tree
5. Exit
========================================"""

_SAMPLE_PROFILES = [
    {
        "label": "Young AI enthusiast (age 22, bachelor)",
        "profile": {
            "age": 22,
            "monthly_income": 15.0,
            "self_learning_hours": 3.5,
            "highest_degree": "bachelor",
            "favourite_domain": "ai",
        },
    },
    {
        "label": "Mid-career software engineer (age 35, master)",
        "profile": {
            "age": 35,
            "monthly_income": 60.0,
            "self_learning_hours": 2.0,
            "highest_degree": "master",
            "favourite_domain": "software_engineering",
        },
    },
    {
        "label": "Data scientist (age 28, master)",
        "profile": {
            "age": 28,
            "monthly_income": 45.0,
            "self_learning_hours": 3.0,
            "highest_degree": "master",
            "favourite_domain": "data_science",
        },
    },
    {
        "label": "Cybersecurity analyst (age 31, bachelor)",
        "profile": {
            "age": 31,
            "monthly_income": 50.0,
            "self_learning_hours": 1.5,
            "highest_degree": "bachelor",
            "favourite_domain": "cybersecurity",
        },
    },
    {
        "label": "Senior business analyst (age 45, phd)",
        "profile": {
            "age": 45,
            "monthly_income": 90.0,
            "self_learning_hours": 1.0,
            "highest_degree": "phd",
            "favourite_domain": "business_analytics",
        },
    },
]


# ── dataset helpers ──────────────────────────────────────────────────────────


def _find_latest_dataset() -> Path | None:
    if not _DATASET_ROOT.is_dir():
        return None
    for folder in reversed(sorted(_DATASET_ROOT.iterdir())):
        candidate = folder / "profiles.json"
        if candidate.is_file():
            return candidate
    return None


def _dataset_is_compatible(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data and isinstance(data, list):
            return "self_learning_hours" in data[0]
    except Exception:
        pass
    return False


def _ensure_dataset() -> Path | None:
    existing = _find_latest_dataset()
    if existing:
        if _dataset_is_compatible(existing):
            return existing
        print("Existing dataset uses old field names — regenerating …")
    else:
        print("No dataset found. Generating 100,000 profiles …")
    _run_build(n=100000, seed=42)
    dataset = _find_latest_dataset()
    if dataset:
        print(f"Dataset ready: {dataset}")
    return dataset


# ── KD-tree pickle helpers ───────────────────────────────────────────────────


def _kdtree_pkl_path(dataset_path: Path) -> Path:
    """Return the canonical pkl path alongside *dataset_path*."""
    return dataset_path.parent / "kdtree.pkl"


def _load_kdtree_pkl(dataset_path: Path) -> KDTreeSearcher | None:
    """Return an unpickled :class:`KDTreeSearcher` if ``kdtree.pkl`` exists, else ``None``."""
    pkl_path = _kdtree_pkl_path(dataset_path)
    if pkl_path.is_file():
        try:
            with pkl_path.open("rb") as fh:
                return pickle.load(fh)  # noqa: S301
        except Exception as exc:
            logger.warning("Failed to load KD-tree pickle (%s) — will rebuild.", exc)
    return None


def _build_and_save_kdtree(dataset_path: Path) -> None:
    """Build :class:`KDTreeSearcher` from *dataset_path* and pickle it next to the JSON."""
    print("Building KD-tree index …")
    try:
        corpuses = Corpuses.from_json_path(dataset_path)
        searcher = KDTreeSearcher(corpuses)
        pkl_path = _kdtree_pkl_path(dataset_path)
        with pkl_path.open("wb") as fh:
            pickle.dump(searcher, fh, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"KD-tree index built and saved to {pkl_path}")
    except Exception as exc:
        print(f"Warning: could not build/save KD-tree index: {exc}")


# ── thin CLI dispatch helpers (no import from main) ──────────────────────────


def _run_build(n: int, seed: int | None) -> int:
    """Call :func:`run_generate_corpus` directly with a synthetic namespace."""
    args = argparse.Namespace(n_profiles=n, seed=seed)
    return run_generate_corpus(args)


def _run_search_cli(
    dataset: Path, query_tmp: str, strategy: str, *, benchmark: bool = False
) -> int:
    """Call :func:`run_search` directly with a synthetic namespace."""
    args = argparse.Namespace(
        dataset=str(dataset),
        query_profile=query_tmp,
        strategy=strategy,
        benchmark=benchmark,
    )
    return run_search(args)


# ── user-input helpers ───────────────────────────────────────────────────────


def _input_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        print(f"  Please enter an integer between {lo} and {hi}.")


def _input_choice(prompt: str, options: tuple[str, ...]) -> str:
    for i, opt in enumerate(options, start=1):
        print(f"    {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(options)}.")


def _build_custom_profile() -> dict:
    print("\n  --- Custom profile ---")
    _DEGREES = ("high_school", "bachelor", "master", "phd")
    _DOMAINS = (
        "ai",
        "software_engineering",
        "data_science",
        "cybersecurity",
        "business_analytics",
    )
    age = _input_int("  age (18–70): ", 18, 70)
    income = _input_int("  monthly_income in million VND (5–100): ", 5, 100)
    hours = _input_int("  self_learning_hours per day (0–4): ", 0, 4)
    print("  highest_degree:")
    degree = _input_choice("  Select [1-4]: ", _DEGREES)
    print("  favourite_domain:")
    domain = _input_choice("  Select [1-5]: ", _DOMAINS)
    return {
        "age": float(age),
        "monthly_income": float(income),
        "self_learning_hours": float(hours),
        "highest_degree": degree,
        "favourite_domain": domain,
    }


def _pick_profile_and_k() -> tuple[dict, int] | None:
    n = len(_SAMPLE_PROFILES)
    print("\nChoose a sample profile:")
    for i, sp in enumerate(_SAMPLE_PROFILES, start=1):
        print(f"  {i}. {sp['label']}")
    print(f"  {n + 1}. Custom (enter manually)")
    print("  0. Cancel")
    while True:
        raw = input(f"Select profile [0-{n + 1}]: ").strip()
        if raw == "0":
            return None
        if raw.isdigit() and int(raw) == n + 1:
            profile = _build_custom_profile()
            break
        if raw.isdigit() and 1 <= int(raw) <= n:
            chosen = _SAMPLE_PROFILES[int(raw) - 1]
            profile = chosen["profile"]
            print(f"\nSearching similar to: {chosen['label']}")
            break
        print(f"  Please enter a number between 0 and {n + 1}.")
    while True:
        raw_k = input("Enter k (number of results, 1–20) [default: 5]: ").strip()
        if raw_k == "":
            k = 5
            break
        if raw_k.isdigit() and 1 <= int(raw_k) <= 20:
            k = int(raw_k)
            break
        print("  k must be an integer between 1 and 20.")
    return profile, k


def _make_query_dict(profile: dict, k: int) -> dict:
    return {
        "profile": profile,
        "weights": {
            "age": 1.0,
            "monthly_income": 1.0,
            "highest_degree": 2.0,
            "self_learning_hours": 1.0,
            "domain": 3.0,
        },
        "k": k,
    }


# ── direct KD-tree query (using pre-built pkl, bypasses CLI) ─────────────────


def _run_kdtree_direct(
    searcher: KDTreeSearcher, dataset: Path, query_dict: dict
) -> None:
    """Execute a KD-tree query via the pre-built *searcher*, bypassing the CLI.

    Loads the corpus for normalization and result lookup; times only the
    :meth:`~KDTreeSearcher.search` call itself.
    """
    try:
        corpuses = Corpuses.from_json_path(dataset)

        # Use a temp file so we go through the validated public API.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(query_dict, tmp)
            tmp_path = tmp.name
        try:
            vq = corpuses.build_vectorized_query(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        t0 = time.perf_counter()
        topk_result = searcher.search(vq.vector, vq.weights, vq.k)
        search_elapsed = time.perf_counter() - t0

        profiles = corpuses.get_profiles(topk_result.profile_ids)
        out: dict = {
            "strategy": "kdtree (pre-built index)",
            "profiles": [asdict(p) for p in profiles],
            "distances": list(topk_result.distances),
            "timing": {
                "build_seconds": 0.0,
                "search_seconds": search_elapsed,
                "note": "index loaded from pkl",
            },
        }
        logger.info("\n%s\n", dump_json(out))
    except Exception as exc:
        print(f"Error during KD-tree search: {exc}")


# ── menu actions ─────────────────────────────────────────────────────────────


def _do_search(strategy: str) -> None:
    dataset = _ensure_dataset()
    if not dataset:
        print("No dataset available — aborting search.")
        return
    result = _pick_profile_and_k()
    if result is None:
        print("Cancelled.")
        return
    profile, k = result
    query_dict = _make_query_dict(profile, k)

    if strategy == "kdtree":
        searcher = _load_kdtree_pkl(dataset)
        if searcher is not None:
            _run_kdtree_direct(searcher, dataset, query_dict)
            return
        print("⚠  KD-tree index not pre-built — building now (this may take a moment) …")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(query_dict, tmp)
        tmp_path = tmp.name
    try:
        _run_search_cli(dataset, tmp_path, strategy)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _do_benchmark() -> None:
    dataset = _ensure_dataset()
    if not dataset:
        print("No dataset available — aborting benchmark.")
        return
    result = _pick_profile_and_k()
    if result is None:
        print("Cancelled.")
        return
    profile, k = result
    query_dict = _make_query_dict(profile, k)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(query_dict, tmp)
        tmp_path = tmp.name

    timings: dict[str, dict] = {}
    kdtree_from_pkl = False

    try:
        # ── Baseline: always fresh build + search ────────────────────────────
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.INFO)
        runner_log = logging.getLogger("services.runner")
        runner_log.addHandler(handler)
        try:
            _run_search_cli(dataset, tmp_path, "baseline", benchmark=True)
        finally:
            runner_log.removeHandler(handler)
        try:
            timings["baseline"] = json.loads(buf.getvalue().strip()).get("timing", {})
        except Exception:
            timings["baseline"] = {}

        # ── KD-tree: load pkl if available, else fall back to CLI ────────────
        pkl_searcher = _load_kdtree_pkl(dataset)
        if pkl_searcher is not None:
            kdtree_from_pkl = True
            try:
                corpuses = Corpuses.from_json_path(dataset)
                vq = corpuses.build_vectorized_query(tmp_path)

                t0 = time.perf_counter()
                pkl_searcher.search(vq.vector, vq.weights, vq.k)
                search_elapsed = time.perf_counter() - t0
                timings["kdtree"] = {"build_seconds": 0.0, "search_seconds": search_elapsed}
            except Exception as exc:
                print(
                    f"Warning: pkl-based KD-tree benchmark failed ({exc})"
                    " — falling back to CLI …"
                )
                kdtree_from_pkl = False

        if not kdtree_from_pkl:
            buf2 = io.StringIO()
            handler2 = logging.StreamHandler(buf2)
            handler2.setLevel(logging.INFO)
            runner_log2 = logging.getLogger("services.runner")
            runner_log2.addHandler(handler2)
            try:
                _run_search_cli(dataset, tmp_path, "kdtree", benchmark=True)
            finally:
                runner_log2.removeHandler(handler2)
            try:
                timings["kdtree"] = json.loads(buf2.getvalue().strip()).get("timing", {})
            except Exception:
                timings["kdtree"] = {}

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    b_build = timings.get("baseline", {}).get("build_seconds", 0.0)
    b_search = timings.get("baseline", {}).get("search_seconds", 0.0)
    k_build = timings.get("kdtree", {}).get("build_seconds", 0.0)
    k_search = timings.get("kdtree", {}).get("search_seconds", 0.0)

    kd_label = "KD-tree (pre-built ✓)" if kdtree_from_pkl else "KD-tree (built fresh)"

    print("\n" + "=" * 60)
    print("  BENCHMARK RESULTS")
    print("=" * 60)
    if kdtree_from_pkl:
        print("  ℹ  KD-tree index loaded from pre-built pkl — build cost = 0")
    else:
        print("  ℹ  KD-tree index built fresh (no pre-built pkl found)")
    print(f"\n  {'':30s} {'Baseline':>10s}   {kd_label}")
    print(f"  {'-'*58}")
    print(
        f"  {'Build time  [O(1) vs O(n log n)]':30s}"
        f" {b_build * 1000:>9.3f}ms   {k_build * 1000:>9.3f}ms"
    )
    print(
        f"  {'Search time [O(n)  vs O(log n)] ':30s}"
        f" {b_search * 1000:>9.3f}ms   {k_search * 1000:>9.3f}ms"
    )
    print(f"\n  {'Amortized cost (total for N queries)':}")
    print(f"    Baseline : N × {b_search * 1000:.3f} ms")
    if kdtree_from_pkl:
        print(
            f"    KD-tree  : 0.000 ms (loaded from index)"
            f" + N × {k_search * 1000:.3f} ms"
        )
    else:
        print(
            f"    KD-tree  : {k_build * 1000:.3f} ms (build once)"
            f" + N × {k_search * 1000:.3f} ms"
        )
    if b_search > k_search and b_search > 0:
        breakeven = (
            math.ceil(k_build / (b_search - k_search)) if k_build > 0 else 1
        )
        print(f"\n   KD-tree is faster than Baseline after {breakeven} queries")
        candidates = sorted(
            {1, max(1, breakeven - 1), breakeven, breakeven + 1, 10 * breakeven}
        )
        for n in candidates:
            bl_total = n * b_search * 1000
            kd_total = k_build * 1000 + n * k_search * 1000
            winner = "KD-tree ✓" if kd_total < bl_total else "Baseline ✓"
            print(
                f"    N={n:5d}:  Baseline={bl_total:8.1f}ms"
                f"  KD-tree={kd_total:8.1f}ms  → {winner}"
            )
    elif k_search >= b_search:
        print("\n  ⚠  KD-tree search is not faster for this dataset size.")
    print("=" * 60)


def _action_generate() -> None:
    existing = _find_latest_dataset()
    if existing:
        answer = (
            input(f"Dataset already exists at {existing}.\nRegenerate? [y/N]: ")
            .strip()
            .lower()
        )
        if answer != "y":
            print("Keeping existing dataset.")
            return
    print("Generating 100,000 profiles …")
    _run_build(n=100000, seed=42)
    dataset = _find_latest_dataset()
    if dataset:
        print(f"Dataset ready: {dataset}")
        _build_and_save_kdtree(dataset)


def interactive_menu() -> None:
    """Launch the numbered interactive menu loop."""
    _ACTIONS: dict[str, tuple[str, object]] = {
        "1": ("Generate dataset", _action_generate),
        "2": ("Baseline search", lambda: _do_search("baseline")),
        "3": ("KD-tree search", lambda: _do_search("kdtree")),
        "4": ("Benchmark", _do_benchmark),
    }
    while True:
        print(_MENU)
        choice = input("Enter option [1-5]: ").strip()
        if choice == "5":
            print("Goodbye!")
            break
        action = _ACTIONS.get(choice)
        if action is None:
            print(f"Invalid option '{choice}' — please enter 1–5.")
            continue
        label, fn = action
        print(f"\n--- {label} ---")
        try:
            fn()  # type: ignore[operator]
        except KeyboardInterrupt:
            print("\n(interrupted)")
        print()
