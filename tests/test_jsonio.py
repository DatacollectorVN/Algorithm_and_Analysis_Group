"""JSON I/O round-trip tests."""

import json
import tempfile
import unittest
from pathlib import Path

from services.constants import DOMAIN_CATALOG, VECTOR_DIM
from services.dataset import Corpuses
from services.dto import Profile
from services.jsonio import load_corpus_json, load_query_json

# Full 9-key weights dict matching QUERY_WEIGHT_KEYS order
_WEIGHTS_9 = {
    "age": 1.0,
    "monthly_income": 1.0,
    "highest_degree": 0.5,
    "self_learning_hours": 1.0,
    "domain_ai": 1.0,
    "domain_software_engineering": 1.0,
    "domain_data_science": 1.0,
    "domain_cybersecurity": 1.0,
    "domain_business_analytics": 1.0,
}


class TestJsonIO(unittest.TestCase):
    def test_corpus_roundtrip(self) -> None:
        rows = [
            {
                "profile_id": 101,
                "age": 22,
                "monthly_income": 40.0,
                "self_learning_hours": 2.5,
                "highest_degree": "bachelor",
                "favourite_domain": "ai",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps(rows), encoding="utf-8")
            got = load_corpus_json(p)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].profile_id, 101)

    def test_query_roundtrip(self) -> None:
        doc = {
            "profile": {
                "profile_id": 9,
                "age": 30,
                "monthly_income": 55.0,
                "self_learning_hours": 3.0,
                "highest_degree": "master",
                "favourite_domain": "data_science",
            },
            "weights": _WEIGHTS_9,
            "k": 3,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            ref, weights, k = load_query_json(p)
            self.assertEqual(k, 3)
            self.assertEqual(len(weights), VECTOR_DIM)
            corpus = [
                Profile(9, 30.0, 55.0, 3.0, "master", "data_science"),
                Profile(8, 40.0, 60.0, 2.0, "bachelor", "ai"),
            ]
            norm, stats = Corpuses.build_normalized_corpus(corpus)
            Corpuses.normalize_query_raw(ref, stats)

    def test_weights_domain_shorthand_onehot(self) -> None:
        """Single ``domain`` scalar expands using profile.favourite_domain."""
        doc = {
            "profile": {
                "profile_id": 9,
                "age": 30,
                "monthly_income": 55.0,
                "self_learning_hours": 3.0,
                "highest_degree": "master",
                "favourite_domain": "data_science",
            },
            "weights": {
                "age": 1.0,
                "monthly_income": 1.0,
                "highest_degree": 0.5,
                "self_learning_hours": 1.0,
                "domain": 5.0,
            },
            "k": 3,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            ref, weights, k = load_query_json(p)
            self.assertEqual(k, 3)
            self.assertEqual(len(weights), VECTOR_DIM)
            idx = DOMAIN_CATALOG.index(ref.favourite_domain)
            self.assertEqual(weights[4 + idx], 5.0)
            self.assertEqual(sum(weights[4:]), 5.0)

    def test_weights_education_key_rejected(self) -> None:
        """Weights must use ``highest_degree``, not ``education``."""
        from services.helper import ValidationError

        doc = {
            "profile": {
                "profile_id": 9,
                "age": 30,
                "monthly_income": 55.0,
                "self_learning_hours": 3.0,
                "highest_degree": "master",
                "favourite_domain": "ai",
            },
            "weights": {
                "age": 1.0,
                "monthly_income": 1.0,
                "education": 0.5,
                "self_learning_hours": 1.0,
                "domain": 2.0,
            },
            "k": 2,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_query_json(p)

    def test_weights_partial_domain_keys_rejected(self) -> None:
        from services.helper import ValidationError

        doc = {
            "profile": {
                "profile_id": 9,
                "age": 30,
                "monthly_income": 55.0,
                "self_learning_hours": 3.0,
                "highest_degree": "master",
                "favourite_domain": "data_science",
            },
            "weights": {
                "age": 1.0,
                "monthly_income": 1.0,
                "highest_degree": 0.5,
                "self_learning_hours": 1.0,
                "domain_ai": 1.0,
            },
            "k": 3,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_query_json(p)


if __name__ == "__main__":
    unittest.main()
