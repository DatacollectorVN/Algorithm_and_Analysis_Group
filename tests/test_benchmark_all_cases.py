"""Tests for the all-cases benchmark helpers added to services/menu.py."""

from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Ensure src/ is on the path when running from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.menu import (
    _SAMPLE_PROFILES,
    _WEIGHT_SCENARIOS,
    _find_or_generate_dataset_for_size,
    _input_int_list,
    _print_all_cases_report,
    _run_case,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_topk(profile_ids: tuple[int, ...], distances: tuple[float, ...]):
    """Return a minimal TopKResult-like object for mocking."""
    from services.dto import TopKResult

    return TopKResult(profile_ids=profile_ids, distances=distances)


# ── T010: _input_int_list ─────────────────────────────────────────────────────


class TestInputIntList(unittest.TestCase):
    """Unit tests for _input_int_list."""

    def _run(self, inputs: list[str]) -> list[int]:
        """Drive _input_int_list with a sequence of simulated inputs."""
        it = iter(inputs)
        with patch("builtins.input", side_effect=it):
            return _input_int_list("sizes: ")

    def test_single_value(self) -> None:
        result = self._run(["42"])
        self.assertEqual(result, [42])

    def test_comma_separated(self) -> None:
        result = self._run(["10000,100000,50000"])
        self.assertEqual(result, [10000, 50000, 100000])  # sorted

    def test_deduplication(self) -> None:
        result = self._run(["5,5,3,5"])
        self.assertEqual(result, [3, 5])

    def test_whitespace_padded(self) -> None:
        result = self._run([" 10 , 20 , 30 "])
        self.assertEqual(result, [10, 20, 30])

    def test_invalid_then_valid(self) -> None:
        with patch("builtins.print"):
            result = self._run(["abc,10", "10,20"])
        self.assertEqual(result, [10, 20])

    def test_negative_rejected(self) -> None:
        with patch("builtins.print"):
            result = self._run(["-1,10", "5"])
        self.assertEqual(result, [5])

    def test_zero_rejected(self) -> None:
        with patch("builtins.print"):
            result = self._run(["0,10", "10"])
        self.assertEqual(result, [10])

    def test_empty_input_reprompts(self) -> None:
        with patch("builtins.print"):
            result = self._run(["", "  ", "7"])
        self.assertEqual(result, [7])


# ── T011: _find_or_generate_dataset_for_size ─────────────────────────────────


class TestFindOrGenerateDatasetForSize(unittest.TestCase):
    """Unit tests for _find_or_generate_dataset_for_size."""

    def test_found_existing(self, tmp_path=None) -> None:
        """Returns existing path when metadata.txt contains the right N=."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "20260101_120000"
            folder.mkdir()
            (folder / "metadata.txt").write_text("N=1000\nseed=42\n", encoding="utf-8")
            dataset_path = folder / "profiles.json"
            # Must satisfy _is_schema_compatible: list with self_learning_hours + integer profile_id
            dataset_path.write_text(
                '[{"profile_id": 1, "age": 22.0, "monthly_income": 15.0,'
                ' "self_learning_hours": 3.5, "highest_degree": "bachelor",'
                ' "favourite_domain": "ai"}]',
                encoding="utf-8",
            )

            with patch("services.menu._DATASET_ROOT", root), patch("builtins.print"):
                result = _find_or_generate_dataset_for_size(1000)

        self.assertEqual(result, dataset_path)

    def test_not_found_generates(self) -> None:
        """Calls run_generate_corpus when no matching dataset exists."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Dataset folder created after generate (simulate)
            generated_folder = root / "20260101_130000"

            def fake_generate(n: int, seed: int | None = None) -> int:
                generated_folder.mkdir(exist_ok=True)
                (generated_folder / "metadata.txt").write_text(
                    f"N={n}\nseed=42\n", encoding="utf-8"
                )
                # Must satisfy _is_schema_compatible
                (generated_folder / "profiles.json").write_text(
                    '[{"profile_id": 1, "age": 22.0, "monthly_income": 15.0,'
                    ' "self_learning_hours": 3.5, "highest_degree": "bachelor",'
                    ' "favourite_domain": "ai"}]',
                    encoding="utf-8",
                )
                return 0

            with (
                patch("services.menu._DATASET_ROOT", root),
                patch("services.menu.run_generate_corpus", side_effect=fake_generate),
                patch("builtins.print"),
            ):
                result = _find_or_generate_dataset_for_size(500)

            # Check existence inside the with-block while the temp dir still exists.
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())

    def test_generation_failure_returns_none(self) -> None:
        """Returns None when generation fails to create the expected file."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            with (
                patch("services.menu._DATASET_ROOT", root),
                patch("services.menu.run_generate_corpus", return_value=0),  # no file created
                patch("builtins.print"),
            ):
                result = _find_or_generate_dataset_for_size(999)

        self.assertIsNone(result)


# ── T012: _run_case correctness flag ──────────────────────────────────────────


class TestRunCase(unittest.TestCase):
    """Unit tests for _run_case correctness checking."""

    def _build_small_corpus(self, n: int = 10):
        """Build a tiny in-memory Corpuses for testing."""
        from services.dataset import Corpuses
        from services.search.strategies import BaselineSearcher, KDTreeSearcher, build_searcher

        profiles = list(Corpuses.iter_synthetic_profiles(n, seed=0))
        corpuses = Corpuses.from_raw(profiles)
        baseline, _ = build_searcher(BaselineSearcher, corpuses)
        kdtree, _ = build_searcher(KDTreeSearcher, corpuses)
        return baseline, kdtree, corpuses

    def test_correct_true_when_strategies_agree(self) -> None:
        baseline, kdtree, corpuses = self._build_small_corpus(50)
        profile_dict = _SAMPLE_PROFILES[0]["profile"]
        weights = _WEIGHT_SCENARIOS[0]["weights"]

        result = _run_case(baseline, kdtree, corpuses, profile_dict, weights, k=3)

        self.assertTrue(result["correct"], "Baseline and KD-tree should agree on small corpus")
        self.assertGreater(result["b_search"], 0.0)
        self.assertGreater(result["k_search"], 0.0)

    def test_correct_false_when_kdtree_returns_wrong_ids(self) -> None:
        from services.dto import TopKResult

        baseline, kdtree, corpuses = self._build_small_corpus(50)
        profile_dict = _SAMPLE_PROFILES[1]["profile"]
        weights = _WEIGHT_SCENARIOS[0]["weights"]

        # Monkey-patch kdtree.search to return completely wrong ids
        wrong_result = TopKResult(profile_ids=(999, 998, 997), distances=(9.9, 9.8, 9.7))
        kdtree.search = lambda *_args, **_kwargs: wrong_result

        result = _run_case(baseline, kdtree, corpuses, profile_dict, weights, k=3)

        self.assertFalse(result["correct"])

    def test_speedup_computed(self) -> None:
        baseline, kdtree, corpuses = self._build_small_corpus(100)
        profile_dict = _SAMPLE_PROFILES[2]["profile"]
        weights = _WEIGHT_SCENARIOS[1]["weights"]

        result = _run_case(baseline, kdtree, corpuses, profile_dict, weights, k=5)

        expected_speedup = result["b_search"] / result["k_search"] if result["k_search"] > 0 else float("inf")
        self.assertAlmostEqual(result["speedup"], expected_speedup, places=10)

    def test_zero_k_search_gives_inf_speedup(self) -> None:
        baseline, kdtree, corpuses = self._build_small_corpus(10)
        profile_dict = _SAMPLE_PROFILES[0]["profile"]
        weights = _WEIGHT_SCENARIOS[0]["weights"]

        # Force k_search timing to 0 by patching get_topk
        from services.dto import TopKResult

        dummy = TopKResult(profile_ids=(1,), distances=(0.0,))

        with patch("services.menu.get_topk") as mock_get_topk:
            mock_get_topk.side_effect = [(dummy, 0.001), (dummy, 0.0)]
            result = _run_case(baseline, kdtree, corpuses, profile_dict, weights, k=1)

        self.assertEqual(result["speedup"], float("inf"))


# ── T013: _print_all_cases_report smoke test ──────────────────────────────────


class TestPrintAllCasesReport(unittest.TestCase):
    """Smoke tests for _print_all_cases_report output format."""

    def _make_row(self, size: int = 1000, k: int = 2, weight_label: str = "Uniform (all 1.0)", correct: bool = True) -> dict:
        return {
            "size": size,
            "k": k,
            "weight_label": weight_label,
            "profile_label": "Young AI enthusiast (age 22, bachelor)",
            "b_build": 0.01,
            "k_build": 0.05,
            "b_search": 0.002,
            "k_search": 0.0001,
            "speedup": 20.0,
            "correct": correct,
        }

    def _capture_report(self, size_rows, k_rows, weight_rows, all_rows) -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            _print_all_cases_report(size_rows, k_rows, weight_rows, all_rows)
        return buf.getvalue()

    def test_four_section_headers_present(self) -> None:
        row = self._make_row()
        weight_row = {**row, "weight_label": "Uniform (all 1.0)"}
        out = self._capture_report([row], [row], [weight_row], [row])

        self.assertIn("Section 1: Effect of Dataset Size", out)
        self.assertIn("Section 2: Effect of k Value", out)
        self.assertIn("Section 3: Effect of Attribute Weights", out)
        self.assertIn("Section 4: Correctness Verification", out)

    def test_correctness_summary_line_present(self) -> None:
        row = self._make_row(correct=True)
        out = self._capture_report([row], [row], [row], [row])
        self.assertIn("Correctness: 1/1 cases passed", out)

    def test_correctness_partial_fail(self) -> None:
        # all_rows has 2 entries: 1 correct, 1 incorrect → "1/2 cases passed"
        all_rows = [self._make_row(correct=True), self._make_row(size=2000, correct=False)]
        single_row = [self._make_row()]
        out = self._capture_report(single_row, single_row, single_row, all_rows)
        self.assertIn("Correctness: 1/2 cases passed", out)

    def test_summary_statistics_present(self) -> None:
        row = self._make_row()
        out = self._capture_report([row], [row], [row], [row])
        self.assertIn("Average speedup", out)
        self.assertIn("Best", out)
        self.assertIn("Worst", out)

    def test_empty_all_rows_no_crash(self) -> None:
        row = self._make_row()
        # Should not raise even with empty all_rows
        out = self._capture_report([row], [row], [row], [])
        self.assertIn("Section 4", out)


if __name__ == "__main__":
    unittest.main()
