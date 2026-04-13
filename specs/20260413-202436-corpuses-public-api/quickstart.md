# Quickstart: using `Corpuses` after the public API change

## Synthetic data

```python
from services.dataset import Corpuses

raw = list(Corpuses.iter_synthetic_profiles(100, seed=42))
corp = Corpuses.from_raw(raw)
```

## Encode + stats + normalize (low-level)

```python
from services.dataset import Corpuses
from services.dto import RawProfile

raw = RawProfile(
    profile_id="p1",
    age=30.0,
    monthly_income=50.0,
    daily_learning_hours=2.0,
    highest_degree="Bachelor",
    favourite_domain="CS",
)
pre = Corpuses.raw_to_prevector(raw)
stats = Corpuses.compute_scaling_stats([pre])
scaled = Corpuses.apply_minmax(pre, stats)
```

## Full normalized corpus tuple (no `Corpuses` wrapper)

```python
from services.dataset import Corpuses

normalized_list, stats = Corpuses.build_normalized_corpus(raw_profiles)
```

## Load from disk + query

```python
from pathlib import Path
from services.dataset import Corpuses

corp = Corpuses.from_json_path(Path("corpus.json"))
vec, weights, k = corp.load_query(Path("query.json"))
```

## Migration from removed module helpers

| Before | After |
|--------|--------|
| `iter_synthetic_profiles(n, seed=s)` | `Corpuses.iter_synthetic_profiles(n, seed=s)` |
| `build_normalized_corpus(raw)` | `Corpuses.build_normalized_corpus(raw)` |
| `normalize_query_raw(r, stats)` | `Corpuses.normalize_query_raw(r, stats)` |
| `degree_to_rank(d)` | `Corpuses.degree_to_rank(d)` |
| `get_synthetic_corpus(path)` | `Corpuses.from_json_path(path)` |
| `get_synthetic_query(path, corp)` | `corp.load_query(path)` |
