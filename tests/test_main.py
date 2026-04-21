"""Tests for ``main`` CLI: ``build`` and ``search`` subcommands (002)."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path

import main


@contextmanager
def _capture_runner_info_log() -> Iterator[StringIO]:
    """Capture ``services.runner`` INFO logs (CLI uses logger, not stdout)."""
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("services.runner")
    old_handlers = list(log.handlers)
    old_propagate = log.propagate
    old_level = log.level
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        yield buf
    finally:
        log.removeHandler(handler)
        log.handlers[:] = old_handlers
        log.propagate = old_propagate
        log.setLevel(old_level)


_CORPUS_KEYS = frozenset(
    {
        "profile_id",
        "age",
        "monthly_income",
        "self_learning_hours",
        "highest_degree",
        "favourite_domain",
    }
)


class TestMainGenerateCorpus(unittest.TestCase):
    """User Story 1: synthetic profiles written under .rmit/dataset/YYYYMMDD_HHMMSS/."""

    def _latest_run_dir(self, base: Path) -> Path:
        root = base / ".rmit" / "dataset"
        self.assertTrue(root.is_dir())
        subdirs = sorted(p for p in root.iterdir() if p.is_dir())
        self.assertGreaterEqual(len(subdirs), 1)
        return subdirs[-1]

    def test_generate_writes_n_profiles_with_dash_n(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            prev = os.getcwd()
            try:
                os.chdir(td_path)
                with _capture_runner_info_log() as buf:
                    rc = main.run(["build", "--n", "7", "--seed", "0"])
                out = buf.getvalue()
                self.assertIn("Dataset:", out)
                self.assertIn("Metadata:", out)
                self.assertIn("profiles.json", out)
                self.assertIn("metadata.txt", out)
            finally:
                os.chdir(prev)
            self.assertEqual(rc, 0)
            run_dir = self._latest_run_dir(td_path)
            corpus_path = run_dir / "profiles.json"
            meta_path = run_dir / "metadata.txt"
            self.assertTrue(re.fullmatch(r"\d{8}_\d{6}", run_dir.name))
            self.assertTrue(corpus_path.is_file())
            self.assertTrue(meta_path.is_file())
            data = json.loads(corpus_path.read_text(encoding="utf-8"))
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 7)
            for row in data:
                self.assertIsInstance(row, dict)
                self.assertEqual(set(row.keys()), _CORPUS_KEYS)
            self.assertEqual(meta_path.read_text(encoding="utf-8"), "N=7\nseed=0\n")

    def test_generate_deterministic_with_seed(self) -> None:
        def run_once() -> str:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                prev = os.getcwd()
                try:
                    os.chdir(td_path)
                    with redirect_stdout(StringIO()):
                        main.run(["build", "--n", "20", "--seed", "42"])
                finally:
                    os.chdir(prev)
                cpath = self._latest_run_dir(td_path) / "profiles.json"
                return cpath.read_text(encoding="utf-8")

        self.assertEqual(run_once(), run_once())

    def test_generate_rejects_n_lt_one(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["build", "--n", "0"])

    def test_generate_rejects_strategy_flag(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["build", "--n", "2", "--strategy", "baseline"])

    def test_generate_rejects_benchmark(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["build", "--n", "2", "--benchmark"])

    def test_generate_requires_n(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["build", "--seed", "1"])


def _sample_corpus_and_query() -> tuple[list[dict], dict]:
    corpus = [
        {
            "profile_id": 1,
            "age": 22,
            "monthly_income": 40.0,
            "self_learning_hours": 2.5,
            "highest_degree": "bachelor",
            "favourite_domain": "software_engineering",
        },
        {
            "profile_id": 2,
            "age": 35,
            "monthly_income": 50.0,
            "self_learning_hours": 3.0,
            "highest_degree": "master",
            "favourite_domain": "data_science",
        },
    ]
    query = {
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
            "domain_software_engineering": 1.0,
            "domain_data_science": 1.0,
            "domain_cybersecurity": 1.0,
            "domain_business_analytics": 1.0,
        },
        "k": 2,
    }
    return corpus, query


class TestMainSearch(unittest.TestCase):
    """Phase 4–5: search subcommand with temp JSON files."""

    def test_search_baseline_returns_hits(self) -> None:
        corpus, query = _sample_corpus_and_query()
        with tempfile.TemporaryDirectory() as td:
            cpath = Path(td) / "c.json"
            qpath = Path(td) / "q.json"
            cpath.write_text(json.dumps(corpus), encoding="utf-8")
            qpath.write_text(json.dumps(query), encoding="utf-8")
            with _capture_runner_info_log() as buf:
                rc = main.run(
                    [
                        "search",
                        "--dataset",
                        str(cpath),
                        "--query-profile",
                        str(qpath),
                        "--strategy",
                        "baseline",
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue().strip())
            self.assertEqual(out["strategy"], "baseline")
            self.assertIn("profiles", out)
            self.assertEqual(len(out["profiles"]), 2)

    def test_search_benchmark_includes_timing(self) -> None:
        corpus, query = _sample_corpus_and_query()
        with tempfile.TemporaryDirectory() as td:
            cpath = Path(td) / "c.json"
            qpath = Path(td) / "q.json"
            cpath.write_text(json.dumps(corpus), encoding="utf-8")
            qpath.write_text(json.dumps(query), encoding="utf-8")
            with _capture_runner_info_log() as buf:
                rc = main.run(
                    [
                        "search",
                        "--dataset",
                        str(cpath),
                        "--query-profile",
                        str(qpath),
                        "--strategy",
                        "baseline",
                        "--benchmark",
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue().strip())
            self.assertIn("timing", out)
            self.assertIn("search_seconds", out["timing"])
            self.assertIn("build_seconds", out["timing"])

    def test_search_kdtree_returns_hits(self) -> None:
        corpus, query = _sample_corpus_and_query()
        with tempfile.TemporaryDirectory() as td:
            cpath = Path(td) / "c.json"
            qpath = Path(td) / "q.json"
            cpath.write_text(json.dumps(corpus), encoding="utf-8")
            qpath.write_text(json.dumps(query), encoding="utf-8")
            with _capture_runner_info_log() as buf:
                rc = main.run(
                    [
                        "search",
                        "--dataset",
                        str(cpath),
                        "--query-profile",
                        str(qpath),
                        "--strategy",
                        "kdtree",
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue().strip())
            self.assertEqual(out["strategy"], "kdtree")
            self.assertEqual(len(out["profiles"]), 2)


class TestMainEndToEnd(unittest.TestCase):
    """Phase 4–6: build output feeds search (temp cwd)."""

    def test_generate_then_search(self) -> None:
        _, query = _sample_corpus_and_query()
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            prev = os.getcwd()
            try:
                os.chdir(td_path)
                with redirect_stdout(StringIO()):
                    rc_gen = main.run(["build", "--n", "5", "--seed", "7"])
                self.assertEqual(rc_gen, 0)
                root = td_path / ".rmit" / "dataset"
                stamp_dirs = sorted(p for p in root.iterdir() if p.is_dir())
                corpus_path = stamp_dirs[-1] / "profiles.json"
                qpath = td_path / "q.json"
                qpath.write_text(json.dumps(query), encoding="utf-8")
                with _capture_runner_info_log() as buf:
                    rc_search = main.run(
                        [
                            "search",
                            "--dataset",
                            str(corpus_path),
                            "--query-profile",
                            str(qpath),
                            "--strategy",
                            "baseline",
                        ]
                    )
            finally:
                os.chdir(prev)
            self.assertEqual(rc_search, 0)
            out = json.loads(buf.getvalue().strip())
            self.assertEqual(len(out["profiles"]), 2)


class TestMainUsage(unittest.TestCase):
    """Invalid subcommand / missing required options."""

    def test_unknown_subcommand(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["not-a-command", "--n", "1"])

    def test_missing_subcommand(self) -> None:
        with self.assertRaises(SystemExit):
            main.run([])

    def test_search_missing_dataset(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["search", "--query-profile", "/tmp/missing.json"])

    def test_search_missing_query_profile(self) -> None:
        with self.assertRaises(SystemExit):
            main.run(["search", "--dataset", "/tmp/missing.json"])


if __name__ == "__main__":
    unittest.main()
