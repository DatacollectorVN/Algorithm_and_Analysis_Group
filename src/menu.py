"""Interactive CLI menu for the Top-K Profile Similarity Search tool."""

from __future__ import annotations

import argparse
import io
import json
import logging
import pickle
import tempfile
import time
from pathlib import Path

from services.dataset import Corpuses
from services.runner import run_generate_corpus, run_search
from services.search.strategies import KDTreeSearcher

logger = logging.getLogger(__name__)

_DATASET_ROOT = Path(".rmit/dataset")
_benchmark_done_this_session: bool = False  # True after first Option-4 run
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


# ── storage pickle helpers ───────────────────────────────────────────────────


def _pkl_path(dataset_path: Path, strategy: str) -> Path:
    return dataset_path.parent / f"{strategy}.pkl"


def _load_pkl(dataset_path: Path, strategy: str):
    p = _pkl_path(dataset_path, strategy)
    if p.is_file():
        try:
            with p.open("rb") as fh:
                return pickle.load(fh)  # noqa: S301
        except Exception as exc:
            logger.warning("Failed to load %s pickle (%s) — will rebuild.", strategy, exc)
    return None


def _save_pkl(dataset_path: Path, strategy: str, searcher) -> None:
    p = _pkl_path(dataset_path, strategy)
    with p.open("wb") as fh:
        pickle.dump(searcher, fh, protocol=pickle.HIGHEST_PROTOCOL)


def _kdtree_pkl_path(dataset_path: Path) -> Path:
    return _pkl_path(dataset_path, "kdtree")


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
    from_pkl: dict[str, bool] = {"baseline": False, "kdtree": False}
    global _benchmark_done_this_session

    # First run this session → delete both pkls so build times are real
    if not _benchmark_done_this_session:
        for s in ("baseline", "kdtree"):
            p = _pkl_path(dataset, s)
            if p.is_file():
                p.unlink()
        print("  ℹ  First run — building both strategies fresh for accurate timing …")

    try:
        corpuses = Corpuses.from_json_path(dataset)
        vq = corpuses.build_vectorized_query(tmp_path)

        for strategy in ("baseline", "kdtree"):
            searcher = _load_pkl(dataset, strategy)
            if searcher is not None:
                from_pkl[strategy] = True
                t0 = time.perf_counter()
                searcher.search(vq.vector, vq.weights, vq.k)
                timings[strategy] = {"build_seconds": 0.0, "search_seconds": time.perf_counter() - t0}
            else:
                # Fresh build via CLI — captures build+search timing
                buf = io.StringIO()
                handler = logging.StreamHandler(buf)
                handler.setLevel(logging.INFO)
                rlog = logging.getLogger("services.runner")
                rlog.addHandler(handler)
                try:
                    _run_search_cli(dataset, tmp_path, strategy, benchmark=True)
                finally:
                    rlog.removeHandler(handler)
                try:
                    timings[strategy] = json.loads(buf.getvalue().strip()).get("timing", {})
                except Exception:
                    timings[strategy] = {}
                # Save searcher for next run
                try:
                    from services.search.strategies import BaselineSearcher
                    built = BaselineSearcher(corpuses) if strategy == "baseline" else KDTreeSearcher(corpuses)
                    _save_pkl(dataset, strategy, built)
                except Exception as exc:
                    logger.warning("Could not save %s pkl: %s", strategy, exc)

        _benchmark_done_this_session = True

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    b_build = timings.get("baseline", {}).get("build_seconds", 0.0)
    b_search = timings.get("baseline", {}).get("search_seconds", 0.0)
    k_build = timings.get("kdtree", {}).get("build_seconds", 0.0)
    k_search = timings.get("kdtree", {}).get("search_seconds", 0.0)

    both_fresh = not from_pkl["baseline"] and not from_pkl["kdtree"]
    both_pkl   = from_pkl["baseline"] and from_pkl["kdtree"]
    b_label = "Baseline (pre-built ✓)" if from_pkl["baseline"] else "Baseline (built fresh)"
    k_label = "KD-tree (pre-built ✓)"  if from_pkl["kdtree"]   else "KD-tree (built fresh)"

    print("\n" + "=" * 62)
    print("  BENCHMARK RESULTS")
    print("=" * 62)
    if both_fresh:
        print("  ℹ  First run — both strategies built fresh (indexes saved for next run)")
    elif both_pkl:
        print("  ℹ  Both indexes loaded from pkl — comparing query time only")
    print(f"\n  {'':30s} {b_label:>20s}   {k_label}")
    print(f"  {'-'*60}")
    print(f"  {'Build time  [O(1) vs O(n log n)]':30s} {b_build * 1000:>19.3f}ms   {k_build * 1000:>9.3f}ms")
    print(f"  {'Search time [O(n)  vs O(log n)] ':30s} {b_search * 1000:>19.3f}ms   {k_search * 1000:>9.3f}ms")
    if b_search > 0 and k_search > 0:
        speedup = b_search / k_search
        print(f"\n  KD-tree query is {speedup:.1f}× faster than Baseline")
    elif k_search >= b_search > 0:
        print("\n  ⚠  KD-tree search is not faster for this dataset size.")
    print("=" * 62)


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
        print("  ℹ  Run Option 4 (Benchmark) to build and persist the KD-tree index.")


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
