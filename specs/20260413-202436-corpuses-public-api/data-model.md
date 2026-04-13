# Data model: Corpus pipeline public API

No new persisted entities. This feature only changes **where** operations live (class public methods vs. module functions).

## Entities (unchanged semantics)

| Concept | Description | Validation / rules |
|---------|-------------|-------------------|
| `RawProfile` | Raw corpus/query record | Valid catalog values for degree and domain; numeric fields as today |
| Pre-vector | 5-tuple of floats | Produced by `Corpuses.raw_to_prevector` |
| `ScalingStats` | Per-dimension min/max | From `Corpuses.compute_scaling_stats`; empty input → error |
| `NormalizedProfile` | id + normalized 5-tuple | From `Corpuses.build_normalized_corpus` or constructors |
| `Corpuses` | Tuple of normalized profiles + `ScalingStats` | Non-empty corpus for `from_raw`; query normalization uses bundled stats |

## State transitions

1. Raw sequence → encode pre-vectors → compute stats → normalize rows → `Corpuses` instance (`from_raw` / `build_normalized_corpus` + `from_normalized` as today).
2. Query: `RawProfile` + stats → `normalize_query_raw` or instance `normalize_query(self.stats)`.

## Invariants preserved

- Same `ValidationError` messages and trigger conditions for empty corpus, unknown categories, etc.
- JSON I/O shapes unchanged (`jsonio` untouched except tests’ imports).
