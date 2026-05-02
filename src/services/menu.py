"""Interactive CLI menu for the Top-K Profile Similarity Search tool."""

from __future__ import annotations

import json
import logging
import math
import pickle
import random
import tempfile
import time
from pathlib import Path

from services.constants import HITS_EQUAL_ABS_TOL, QUERY_WEIGHT_KEYS
from services.dataset import Corpuses
from services.dto import QProfile, VectorizedQueryProfile
from services.runner import run_generate_corpus, run_search
from services.search.strategies import BaselineSearcher, KDTreeSearcher, build_searcher, get_topk

logger = logging.getLogger(__name__)

_DATASET_ROOT = Path(".rmit/dataset")
_benchmark_done_this_session: bool = False  # True after first Option-4 run
_MENU = """
========================================
  Top-K Profile Similarity Search
========================================
1. Generate dataset (choose sample size)
2. Search with Baseline strategy
3. Search with KD-tree strategy
4. Simple Benchmark: Baseline vs KD-tree
5. Run All Cases Benchmark: Baseline vs KD-tree
6. Exit
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

# Weight scenarios for the all-cases benchmark (Section 3: Effect of Attribute Weights).
# Each tuple is 9-dimensional in QUERY_WEIGHT_KEYS order:
#   (age, monthly_income, self_learning_hours, highest_degree,
#    domain_ai, domain_software_engineering, domain_data_science,
#    domain_cybersecurity, domain_business_analytics)
_WEIGHT_SCENARIOS: list[dict] = [
    {
        "label": "Uniform (all 1.0)",
        "weights": (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    },
    {
        "label": "Domain-heavy (domain x5)",
        "weights": (1.0, 1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 5.0, 5.0),
    },
    {
        "label": "Degree-heavy (degree x5)",
        "weights": (1.0, 1.0, 1.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    },
    {
        "label": "Income-heavy (income x5)",
        "weights": (1.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    },
]


# ── dataset helpers ──────────────────────────────────────────────────────────
def _metadata_dataset_n(metadata: str) -> int | None:
    for raw_line in metadata.splitlines():
        line = raw_line.strip()
        if line.startswith("N="):
            try:
                return int(line[2:].strip())
            except ValueError:
                return None
    return None


def _find_latest_dataset() -> Path | None:
    if not _DATASET_ROOT.is_dir():
        return None
    folders = list(_DATASET_ROOT.iterdir())
    if not folders:
        return None

    tar_folder: Path = max(folders, key=lambda x: x.stat().st_mtime)
    dataset_path: Path = tar_folder / "profiles.json"
    metadata_path: Path = tar_folder / "metadata.txt"
    if metadata_path.is_file() and dataset_path.is_file():
        metadata = metadata_path.read_text(encoding="utf-8")
        n = _metadata_dataset_n(metadata)
        if n is not None:
            print(f"Target Dataset: {dataset_path.resolve()}\nDataset Size: {n}")
            return dataset_path
        else:
            return None
    else:
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
    run_generate_corpus(100000, seed=42)
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


def _input_non_negative_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            v = float(raw)
        except ValueError:
            print("  Please enter a non-negative number.")
            continue
        if not math.isfinite(v) or v < 0.0:
            print("  Weight must be a non-negative finite number.")
            continue
        return v


def _default_interactive_search_weights() -> dict[str, float]:
    """Default weights for preset sample profiles (search / simple benchmark)."""
    return {
        "age": 1.0,
        "monthly_income": 1.0,
        "highest_degree": 2.0,
        "self_learning_hours": 1.0,
        "domain": 3.0,
    }


def _uniform_query_weights() -> dict[str, float]:
    """1.0 on every normalized dimension (``QUERY_WEIGHT_KEYS`` order)."""
    return {k: 1.0 for k in QUERY_WEIGHT_KEYS}


def _read_custom_property_weights() -> dict[str, float]:
    while True:
        print("\n  Enter a non-negative weight for each property:")
        w = {
            "age": _input_non_negative_float("    age: "),
            "monthly_income": _input_non_negative_float("    monthly_income: "),
            "self_learning_hours": _input_non_negative_float("    self_learning_hours: "),
            "highest_degree": _input_non_negative_float("    highest_degree: "),
            "domain": _input_non_negative_float(
                "    favourite_domain (weight on your selected domain): "
            ),
        }
        if any(v > 0.0 for v in w.values()):
            return w
        print("  At least one weight must be positive — try again.")


def _prompt_weights_for_custom_profile() -> dict[str, float]:
    """After a custom profile: uniform 1.0 on all dimensions, or five property weights."""
    while True:
        raw = input(
            "  Use uniform weights (1.0 on every dimension)? [Y/n]: "
        ).strip()
        if raw == "" or raw.lower() == "y":
            return _uniform_query_weights()
        if raw in ("n", "N"):
            return _read_custom_property_weights()
        print("  Press Enter or Y for uniform, or N to set each property's weight.")


def _input_int_list(prompt: str) -> list[int]:
    """Read a comma-separated list of positive integers from stdin.

    Reprompts until all values are valid positive integers. Returns a
    sorted, deduplicated list.

    Args:
        prompt: Message shown to the user.

    Returns:
        Sorted list of unique positive integers.
    """
    while True:
        raw = input(prompt).strip()
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not parts:
            print("  Please enter at least one positive integer.")
            continue
        valid = True
        values: list[int] = []
        for part in parts:
            if part.isdigit() and int(part) > 0:
                values.append(int(part))
            else:
                print(f"  Invalid value '{part}' — all entries must be positive integers.")
                valid = False
                break
        if valid:
            return sorted(set(values))


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


def _pick_profile_and_k() -> tuple[dict, int, dict[str, float]] | None:
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
            weights = _prompt_weights_for_custom_profile()
            break
        if raw.isdigit() and 1 <= int(raw) <= n:
            chosen = _SAMPLE_PROFILES[int(raw) - 1]
            profile = chosen["profile"]
            weights = _default_interactive_search_weights()
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
    return profile, k, weights


def _make_query_dict(profile: dict, k: int, weights: dict[str, float]) -> dict:
    return {
        "profile": profile,
        "weights": weights,
        "k": k,
    }


def _print_search_query_summary(query: dict) -> None:
    """Print query profile, k, and weights before top-k JSON (menu search)."""
    profile = query["profile"]
    w = query["weights"]
    k = query["k"]
    print("\n  --- Search query (before top-k) ---")
    print("  Profile:")
    print(f"    age:                  {profile['age']}")
    print(f"    monthly_income:       {profile['monthly_income']}")
    print(f"    self_learning_hours:  {profile['self_learning_hours']}")
    print(f"    highest_degree:       {profile['highest_degree']}")
    print(f"    favourite_domain:     {profile['favourite_domain']}")
    print(f"  k: {k}")
    print("  Weights:")
    if all(key in w for key in QUERY_WEIGHT_KEYS):
        for key in QUERY_WEIGHT_KEYS:
            print(f"    {key}: {w[key]}")
    else:
        order_labels: tuple[tuple[str, str], ...] = (
            ("age", "age"),
            ("monthly_income", "monthly_income"),
            ("self_learning_hours", "self_learning_hours"),
            ("highest_degree", "highest_degree"),
            ("domain", "favourite_domain (domain axis)"),
        )
        seen: set[str] = set()
        for json_key, label in order_labels:
            if json_key in w:
                print(f"    {label}: {w[json_key]}")
                seen.add(json_key)
        for key in sorted(w):
            if key not in seen:
                print(f"    {key}: {w[key]}")
    print("  " + "-" * 40)


# ── all-cases benchmark helpers ──────────────────────────────────────────────


def _profiles_json_schema_compatible(path: Path) -> bool:
    """Return True when dataset uses the current schema (new field names + integer profile_id)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not (data and isinstance(data, list)):
            return False
        first = data[0]
        if "self_learning_hours" not in first:
            return False
        int(first["profile_id"])  # old format uses "synth-0" strings
        return True
    except Exception:
        return False


def _scan_dataset_root_for_size(size: int) -> tuple[Path | None, bool]:
    """Return (first compatible profiles.json path or None, True if any incompatible match found)."""
    compatible: Path | None = None
    has_incompatible = False
    if not _DATASET_ROOT.is_dir():
        return compatible, has_incompatible
    for folder in _DATASET_ROOT.iterdir():
        if not folder.is_dir():
            continue
        meta = folder / "metadata.txt"
        dataset = folder / "profiles.json"
        if meta.is_file() and dataset.is_file():
            for line in meta.read_text(encoding="utf-8").splitlines():
                if line.strip() == f"N={size}":
                    if _profiles_json_schema_compatible(dataset):
                        compatible = dataset
                    else:
                        has_incompatible = True
    return compatible, has_incompatible


def _find_or_generate_dataset_for_size(size: int) -> Path | None:
    """Find an existing dataset of the given size or generate a fresh one.

    Scans ``.rmit/dataset/*/metadata.txt`` for a line ``N=<size>`` and returns
    the corresponding ``profiles.json`` path if found. Otherwise calls
    :func:`run_generate_corpus` with ``seed=42`` and rescans.

    Args:
        size: Number of profiles required.

    Returns:
        Absolute path to the matching ``profiles.json``, or ``None`` if
        generation fails.
    """
    compatible, has_incompatible = _scan_dataset_root_for_size(size)
    if compatible:
        print(f"  Found existing dataset (N={size:,}): {compatible}")
        return compatible

    if has_incompatible:
        print(f"  Existing dataset (N={size:,}) uses old schema — regenerating …")

    print(f"  Generating dataset (N={size:,}, seed=42) …")
    run_generate_corpus(size, seed=42)
    compatible, _ = _scan_dataset_root_for_size(size)
    if compatible is None:
        print(f"  Warning: Failed to generate or locate dataset for N={size:,}.")
    return compatible


def _run_case(
    baseline: BaselineSearcher,
    kdtree: KDTreeSearcher,
    corpuses: Corpuses,
    profile_dict: dict,
    weights: tuple[float, ...],
    k: int,
) -> dict:
    """Run one benchmark case on both strategies and check correctness.

    Builds a :class:`~services.dto.VectorizedQueryProfile` directly from
    ``profile_dict`` using the corpus scaling stats — no temp file I/O.

    Args:
        baseline: Built baseline strategy instance.
        kdtree: Built KD-tree strategy instance.
        corpuses: Corpus used to normalize the query vector.
        profile_dict: Raw profile fields (age, monthly_income, etc.).
        weights: 9-dimensional weight tuple in ``QUERY_WEIGHT_KEYS`` order.
        k: Number of top results to retrieve.

    Returns:
        Dict with keys ``b_search`` (seconds), ``k_search`` (seconds),
        ``speedup`` (ratio), ``correct`` (bool).
    """
    qprofile = QProfile(
        age=float(profile_dict["age"]),
        monthly_income=float(profile_dict["monthly_income"]),
        self_learning_hours=float(profile_dict["self_learning_hours"]),
        highest_degree=str(profile_dict["highest_degree"]),
        favourite_domain=str(profile_dict["favourite_domain"]),
    )
    vector = corpuses.normalize_query(qprofile)
    vq = VectorizedQueryProfile(vector=vector, weights=weights, k=k)

    b_result, b_search = get_topk(baseline, vq.vector, vq.weights, vq.k)
    k_result, k_search = get_topk(kdtree, vq.vector, vq.weights, vq.k)

    ids_match = b_result.profile_ids == k_result.profile_ids
    paired = len(b_result.distances) == len(k_result.distances)
    dists_match = paired and all(
        abs(bd - kd) <= HITS_EQUAL_ABS_TOL for bd, kd in zip(b_result.distances, k_result.distances)
    )

    # A case is correct only when both methods return the same IDs and near-equal distances.
    correct = ids_match and dists_match
    speedup = (b_search / k_search) if k_search > 0.0 else float("inf")

    if paired and b_result.distances:
        dist_errs = [abs(bd - kd) for bd, kd in zip(b_result.distances, k_result.distances)]
        max_dist_err: float = max(dist_errs)
        avg_dist_err: float = sum(dist_errs) / len(dist_errs)
    else:
        max_dist_err = float("nan")
        avg_dist_err = float("nan")

    return {
        "b_search": b_search,
        "k_search": k_search,
        "speedup": speedup,
        "correct": correct,
        "max_dist_err": max_dist_err,
        "avg_dist_err": avg_dist_err,
    }


def _print_all_cases_report(
    size_rows: list[dict],
    k_rows: list[dict],
    weight_rows: list[dict],
    all_rows: list[dict],
) -> None:
    """Render the four-section all-cases benchmark report to stdout.

    Args:
        size_rows: Per-size timing records for Section 1.
        k_rows: Per-k timing records for Section 2.
        weight_rows: Per-weight-scenario records for Section 3.
        all_rows: All (size, k, weight, profile) records for Section 4 and summary.
    """
    W = 74
    sep = "=" * W

    def _ms(s: float) -> str:
        return f"{s * 1000:>9.2f} ms"

    def _spd(s: float) -> str:
        if s == float("inf"):
            return "      inf"
        return f"{s:>7.2f}x"

    print("\n" + sep)
    print("  BENCHMARK — ALL CASES: Baseline vs KD-tree")
    print(sep)

    # ── Section 1: Effect of Dataset Size ────────────────────────────────────
    first_k = size_rows[0]["k"] if size_rows else "?"
    print(f"\n  --- Section 1: Effect of Dataset Size ---")
    print(f"  (k={first_k}, weights=Uniform, random query per size)")
    print()
    print(
        f"  {'Size':>10}  {'B Build':>11}  {'KD Build':>11}  {'B Search':>11}  {'KD Search':>11}  {'Speedup':>9}"
    )
    print("  " + "-" * 68)
    for r in size_rows:
        print(
            f"  {r['size']:>10,}  {_ms(r['b_build'])}  {_ms(r['k_build'])}"
            f"  {_ms(r['b_search'])}  {_ms(r['k_search'])}  {_spd(r['speedup'])}"
        )

    # ── Section 2: Effect of k Value ─────────────────────────────────────────
    print(f"\n  --- Section 2: Effect of k Value ---")
    print(f"  (all dataset sizes x all k values, weights=Uniform, random query per case)")
    print()
    print(f"  {'Size':>10}  {'k':>4}  {'B Search':>11}  {'KD Search':>11}  {'Speedup':>9}")
    print("  " + "-" * 54)
    for r in k_rows:
        print(
            f"  {r['size']:>10,}  {r['k']:>4}  {_ms(r['b_search'])}  {_ms(r['k_search'])}  {_spd(r['speedup'])}"
        )

    # ── Section 3: Effect of Attribute Weights ────────────────────────────────
    fixed_profile_label = _SAMPLE_PROFILES[0]["label"]
    first_k_label = str(weight_rows[0]["k"]) if weight_rows else "?"
    print(f"\n  --- Section 3: Effect of Attribute Weights ---")
    print(
        f'  (all dataset sizes x all weight scenarios, k={first_k_label}, fixed profile: "{fixed_profile_label}")'
    )
    print()
    print(
        f"  {'Size':>10}  {'Weight Scenario':<30}  {'B Search':>11}  {'KD Search':>11}  {'Speedup':>9}"
    )
    print("  " + "-" * 79)
    for r in weight_rows:
        label = r["weight_label"][:30]
        print(
            f"  {r['size']:>10,}  {label:<30}  {_ms(r['b_search'])}  {_ms(r['k_search'])}  {_spd(r['speedup'])}"
        )

    # ── Section 4: Correctness Verification ──────────────────────────────────
    print(f"\n  --- Section 4: Correctness Verification ---")
    print()
    print(f"  {'Size':>10}  {'k':>4}  {'Weight':<30}  {'Profile':<34}  {'OK?':>4}")
    print("  " + "-" * 88)
    for r in all_rows:
        mark = "Y" if r["correct"] else "N"
        wlabel = r["weight_label"][:30]
        plabel = r["profile_label"][:34]
        print(f"  {r['size']:>10,}  {r['k']:>4}  {wlabel:<30}  {plabel:<34}  {mark:>4}")

    passed = sum(1 for r in all_rows if r["correct"])
    total = len(all_rows)
    pct = (100 * passed // total) if total else 0
    print(f"\n  Correctness: {passed}/{total} cases passed ({pct}%)")

    # ── Table 5: Correctness Verification Summary (All Scenarios) ────────────
    def _aggregate(rows: list[dict]) -> dict:
        n = len(rows)
        if n == 0:
            return {
                "total": 0,
                "matches": 0,
                "rate": 0.0,
                "max_dist_err": float("nan"),
                "avg_dist_err": float("nan"),
                "avg_b_search": 0.0,
                "avg_k_search": 0.0,
            }
        matches = sum(1 for r in rows if r["correct"])
        rate = 100.0 * matches / n
        _nan = float("nan")
        valid_max = [v for r in rows if (v := r.get("max_dist_err", _nan)) == v]
        valid_avg = [v for r in rows if (v := r.get("avg_dist_err", _nan)) == v]
        max_err = max(valid_max) if valid_max else float("nan")
        avg_err = sum(valid_avg) / len(valid_avg) if valid_avg else float("nan")
        avg_b = sum(r["b_search"] for r in rows) / n
        avg_k = sum(r["k_search"] for r in rows) / n
        return {
            "total": n,
            "matches": matches,
            "rate": rate,
            "max_dist_err": max_err,
            "avg_dist_err": avg_err,
            "avg_b_search": avg_b,
            "avg_k_search": avg_k,
        }

    def _err_str(v: float) -> str:
        if v != v:  # NaN
            return f"{'N/A':>10}"
        return f"{v:>10.2e}"

    scenarios = [
        ("A — Dataset size", size_rows),
        ("B — k value", k_rows),
        ("C — Weight config", weight_rows),
    ]
    print(f"\n  --- Table 5: Correctness Verification Summary (All Scenarios) ---")
    print("  Confirm KD-Tree returns identical results to Baseline across all test cases")
    print()
    hdr = (
        f"  {'Scenario':<22}  {'Total':>6}  {'Matches':>8}  {'Rate':>7}"
        f"  {'Max Dist Err':>12}  {'Avg Dist Err':>12}"
        f"  {'Avg B Search':>12}  {'Avg KD Search':>13}"
    )
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for label, rows in scenarios:
        agg = _aggregate(rows)
        rate_str = f"{agg['rate']:>6.1f}%"
        print(
            f"  {label:<22}  {agg['total']:>6}  {agg['matches']:>8}  {rate_str}"
            f"  {_err_str(agg['max_dist_err'])}  {_err_str(agg['avg_dist_err'])}"
            f"  {_ms(agg['avg_b_search'])}  {_ms(agg['avg_k_search'])}"
        )

    # ── Summary (US2: Aggregated Statistics) ─────────────────────────────────
    if all_rows:
        finite = [r["speedup"] for r in all_rows if r["speedup"] != float("inf")]
        if finite:
            avg = sum(finite) / len(finite)
            best = max(
                all_rows, key=lambda r: r["speedup"] if r["speedup"] != float("inf") else -1.0
            )
            worst = min(
                all_rows,
                key=lambda r: r["speedup"] if r["speedup"] != float("inf") else float("inf"),
            )
            print(f"\n  Summary across all {total} cases:")
            print(f"    Average speedup : {avg:.2f}x")
            print(
                f"    Best  speedup   : {_spd(best['speedup'])}"
                f"  (N={best['size']:,}, k={best['k']}, {best['weight_label'][:28]})"
            )
            print(
                f"    Worst speedup   : {_spd(worst['speedup'])}"
                f"  (N={worst['size']:,}, k={worst['k']}, {worst['weight_label'][:28]})"
            )

    print("\n" + sep)


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
    profile, k, weights = result
    query_dict = _make_query_dict(profile, k, weights)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(query_dict, tmp)
        tmp_path = tmp.name
    try:
        _print_search_query_summary(query_dict)
        run_search(dataset, tmp_path, strategy)
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
    profile, k, weights = result
    query_dict = _make_query_dict(profile, k, weights)

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
        print("  First run — building both strategies fresh for accurate timing …")

    try:
        corpuses = Corpuses.from_json_path(dataset)
        vq = corpuses.build_vectorized_query(tmp_path)

        for strategy in ("baseline", "kdtree"):
            searcher = _load_pkl(dataset, strategy)
            if searcher is not None:
                from_pkl[strategy] = True
                t0 = time.perf_counter()
                searcher.search(vq.vector, vq.weights, vq.k)
                timings[strategy] = {
                    "build_seconds": 0.0,
                    "search_seconds": time.perf_counter() - t0,
                }
            else:
                searcher_cls = BaselineSearcher if strategy == "baseline" else KDTreeSearcher
                built, build_elapsed = build_searcher(searcher_cls, corpuses)
                _, search_elapsed = get_topk(built, vq.vector, vq.weights, vq.k)
                timings[strategy] = {
                    "build_seconds": build_elapsed,
                    "search_seconds": search_elapsed,
                }
                try:
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
    both_pkl = from_pkl["baseline"] and from_pkl["kdtree"]
    b_label = "Baseline (pre-built)" if from_pkl["baseline"] else "Baseline (built fresh)"
    k_label = "KD-tree (pre-built)" if from_pkl["kdtree"] else "KD-tree (built fresh)"

    print("\n" + "=" * 62)
    print("  BENCHMARK RESULTS")
    print("=" * 62)
    if both_fresh:
        print("  First run — both strategies built fresh (indexes saved for next run)")
    elif both_pkl:
        print("  Both indexes loaded from pkl — comparing query time only")
    print(f"\n  {'':30s} {b_label:>20s}   {k_label}")
    print(f"  {'-' * 60}")
    print(
        f"  {'Build time  [O(1) vs O(n log n)]':30s} {b_build * 1000:>19.3f}ms   {k_build * 1000:>9.3f}ms"
    )
    print(
        f"  {'Search time [O(n)  vs O(log n)] ':30s} {b_search * 1000:>19.3f}ms   {k_search * 1000:>9.3f}ms"
    )
    if b_search > 0 and k_search > 0:
        speedup = b_search / k_search
        print(f"\n  KD-tree query is {speedup:.1f}x faster than Baseline")
    elif k_search >= b_search > 0:
        print("\n  Warning: KD-tree search is not faster for this dataset size.")
    print("=" * 62)


def _do_benchmark_all_cases() -> None:
    """Interactive all-cases benchmark: Baseline vs KD-tree across sizes, k values, and weights.

    Prompts the user for comma-separated dataset sizes and k values. For each
    requested size, finds or generates a dataset and builds both strategies once.
    Runs a matrix of cases across four report sections:

    1. Effect of dataset size  — fixed k and uniform weights, random profile per size
    2. Effect of k value       — fixed first size and uniform weights, random profile per k
    3. Effect of attribute weights — fixed first size and first k, all weight scenarios
    4. Correctness verification — all (size, k, weight) combinations
    """
    print("\n  --- All Cases Benchmark: Baseline vs KD-tree ---")
    print("  Provide comma-separated lists (e.g. 10000,100000)")

    dataset_sizes = _input_int_list("  Dataset sizes  : ")
    k_values_raw = _input_int_list("  k values       : ")

    # Validate and cap k values
    k_values: list[int] = []
    for kv in k_values_raw:
        if kv > 20:
            print(f"  Warning: k={kv} exceeds maximum of 20 — capping at 20.")
            k_values.append(20)
        else:
            k_values.append(kv)
    k_values = sorted(set(k_values))

    # ── build strategies for each dataset size ───────────────────────────────
    print()
    built: dict[int, dict] = {}
    for size in dataset_sizes:
        path = _find_or_generate_dataset_for_size(size)
        if path is None:
            print(f"  Skipping N={size:,} (dataset unavailable).")
            continue
        print(f"  Building strategies for N={size:,} …", flush=True)
        try:
            corpuses = Corpuses.from_json_path(path)
            b_searcher, b_build = build_searcher(BaselineSearcher, corpuses)
            k_searcher, k_build = build_searcher(KDTreeSearcher, corpuses)
        except Exception as exc:
            print(f"  Error building strategies for N={size:,}: {exc}")
            continue
        print(f"    Baseline: {b_build * 1000:.1f} ms  |  KD-tree: {k_build * 1000:.1f} ms")
        built[size] = {
            "corpuses": corpuses,
            "baseline": b_searcher,
            "kdtree": k_searcher,
            "b_build": b_build,
            "k_build": k_build,
        }
    if not built:
        print("  No datasets available — aborting.")
        return

    available_sizes = [s for s in dataset_sizes if s in built]
    first_k = k_values[0]
    uniform_weights: tuple[float, ...] = _WEIGHT_SCENARIOS[0]["weights"]
    fixed_sp = _SAMPLE_PROFILES[0]
    rng = random.Random()

    # ── Section 1: Effect of dataset size ────────────────────────────────────
    # Fixed: k=first_k, uniform weights; random profile per size
    size_rows: list[dict] = []
    for size in available_sizes:
        b = built[size]
        sp = rng.choice(_SAMPLE_PROFILES)
        rec = _run_case(
            b["baseline"],
            b["kdtree"],
            b["corpuses"],
            sp["profile"],
            uniform_weights,
            first_k,
        )
        size_rows.append(
            {
                "size": size,
                "k": first_k,
                "b_build": b["b_build"],
                "k_build": b["k_build"],
                "profile_label": sp["label"],
                **rec,
            }
        )

    # ── Section 2: Effect of k value ─────────────────────────────────────────
    # All sizes × all k values; uniform weights; random profile per (size, k)
    k_rows: list[dict] = []
    for size in available_sizes:
        b = built[size]
        for kv in k_values:
            sp = rng.choice(_SAMPLE_PROFILES)
            rec = _run_case(
                b["baseline"],
                b["kdtree"],
                b["corpuses"],
                sp["profile"],
                uniform_weights,
                kv,
            )
            k_rows.append(
                {
                    "size": size,
                    "k": kv,
                    "b_build": b["b_build"],
                    "k_build": b["k_build"],
                    "profile_label": sp["label"],
                    **rec,
                }
            )

    # ── Section 3: Effect of attribute weights ────────────────────────────────
    # All sizes × all weight scenarios; fixed k=first_k; fixed profile
    weight_rows: list[dict] = []
    for size in available_sizes:
        b = built[size]
        for ws in _WEIGHT_SCENARIOS:
            rec = _run_case(
                b["baseline"],
                b["kdtree"],
                b["corpuses"],
                fixed_sp["profile"],
                ws["weights"],
                first_k,
            )
            weight_rows.append(
                {
                    "size": size,
                    "k": first_k,
                    "weight_label": ws["label"],
                    "b_build": b["b_build"],
                    "k_build": b["k_build"],
                    **rec,
                }
            )

    # ── All rows: every (size, k, weight, random profile) combination ─────────
    all_rows: list[dict] = []
    for size in available_sizes:
        b = built[size]
        for kv in k_values:
            for ws in _WEIGHT_SCENARIOS:
                sp = rng.choice(_SAMPLE_PROFILES)
                rec = _run_case(
                    b["baseline"],
                    b["kdtree"],
                    b["corpuses"],
                    sp["profile"],
                    ws["weights"],
                    kv,
                )
                all_rows.append(
                    {
                        "size": size,
                        "k": kv,
                        "weight_label": ws["label"],
                        "profile_label": sp["label"],
                        **rec,
                    }
                )

    _print_all_cases_report(size_rows, k_rows, weight_rows, all_rows)


def _action_generate() -> None:
    existing = _find_latest_dataset()
    if existing:
        answer = (
            input(f"Dataset already exists at {existing}.\nRegenerate? [y/N]: ").strip().lower()
        )
        if answer != "y":
            print("Keeping existing dataset.")
            return
    while True:
        raw_n = input("Enter sample size (number of profiles) [default: 100000]: ").strip()
        if raw_n == "":
            n_profiles = 100000
            break
        if raw_n.isdigit() and int(raw_n) > 0:
            n_profiles = int(raw_n)
            break
        print("  Please enter a positive integer (e.g., 100000).")
    print(f"Generating {n_profiles:,} profiles …")
    run_generate_corpus(n_profiles, seed=42)
    dataset = _find_latest_dataset()
    if dataset:
        print(f"Dataset ready: {dataset}")
        print("  Run Option 4 (Simple Benchmark) to build and persist the KD-tree index.")


def interactive_menu() -> None:
    """Launch the numbered interactive menu loop."""
    _ACTIONS: dict[str, tuple[str, object]] = {
        "1": ("Generate dataset", _action_generate),
        "2": ("Baseline search", lambda: _do_search("baseline")),
        "3": ("KD-tree search", lambda: _do_search("kdtree")),
        "4": ("Simple Benchmark", _do_benchmark),
        "5": ("Run All Cases Benchmark", _do_benchmark_all_cases),
    }
    while True:
        print(_MENU)
        choice = input("Enter option [1-6]: ").strip()
        if choice == "6":
            print("Goodbye!")
            break
        action = _ACTIONS.get(choice)
        if action is None:
            print(f"Invalid option '{choice}' — please enter 1–6.")
            continue
        label, fn = action
        print(f"\n--- {label} ---")
        try:
            fn()  # type: ignore[operator]
        except KeyboardInterrupt:
            print("\n(interrupted)")
        print()
