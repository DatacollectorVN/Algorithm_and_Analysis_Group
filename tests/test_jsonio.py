"""JSON I/O round-trip tests."""

import json
import tempfile
import unittest
from pathlib import Path

from services.dataset import Corpuses
from services.dto import RawProfile
from services.jsonio import load_corpus_json, load_query_json


class TestJsonIO(unittest.TestCase):
    def test_corpus_roundtrip(self) -> None:
        rows = [
            {
                "profile_id": "p1",
                "age": 22,
                "monthly_income": 40.0,
                "daily_learning_hours": 2.5,
                "highest_degree": "bachelor",
                "favourite_domain": "software",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"
            p.write_text(json.dumps(rows), encoding="utf-8")
            got = load_corpus_json(p)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0].profile_id, "p1")

    def test_query_roundtrip(self) -> None:
        doc = {
            "reference": {
                "profile_id": "q",
                "age": 30,
                "monthly_income": 55.0,
                "daily_learning_hours": 3.0,
                "highest_degree": "master",
                "favourite_domain": "finance",
            },
            "weights": {
                "age": 1.0,
                "monthly_income": 1.0,
                "education": 0.5,
                "daily_learning_hours": 1.0,
                "domain": 1.0,
            },
            "k": 3,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            ref, weights, k = load_query_json(p)
            self.assertEqual(k, 3)
            self.assertEqual(len(weights), 5)
            corpus = [
                RawProfile("q", 30.0, 55.0, 3.0, "master", "finance"),
                RawProfile("o", 40.0, 60.0, 2.0, "bachelor", "software"),
            ]
            norm, stats = Corpuses.build_normalized_corpus(corpus)
            Corpuses.normalize_query_raw(ref, stats)


if __name__ == "__main__":
    unittest.main()
