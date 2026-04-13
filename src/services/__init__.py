"""Application services: similarity search, I/O, dataset preparation, and helpers."""

from services.args import build_parser
from services.dataset import Corpuses, build_normalized_corpus
from services.dto import NormalizedProfile, RawProfile, ScalingStats
from services.helper import LookalikeSearchError, ValidationError
from services.jsonio import dump_json, load_corpus_json, load_query_json
from services.runner import run_generate_corpus, run_search

__all__ = [
    "LookalikeSearchError",
    "ValidationError",
    "RawProfile",
    "NormalizedProfile",
    "ScalingStats",
    "Corpuses",
    "build_normalized_corpus",
    "dump_json",
    "load_corpus_json",
    "load_query_json",
    "build_parser",
    "run_generate_corpus",
    "run_search",
]
