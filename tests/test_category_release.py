import hashlib
import json
import re
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_category_chart_20260719 import CATEGORIES, HOSTS, load_groups, render_svg


RESULTS = ROOT / "results/verified/2026-07-19-category-rankings/category-rankings.json"


class CategoryReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(RESULTS.read_text(encoding="utf-8"))
        cls.rows = cls.payload["rows"]

    def test_release_has_all_expected_public_groups(self):
        self.assertEqual(len(self.rows), 20)
        self.assertEqual({row["category"] for row in self.rows}, set(CATEGORIES))
        self.assertEqual({row["host"] for row in self.rows}, set(HOSTS))
        self.assertEqual(
            {(row["category"], row["host"]) for row in self.rows},
            {(category, host) for category in CATEGORIES for host in HOSTS},
        )

    def test_ranks_follow_quality_first_policy(self):
        groups = defaultdict(list)
        for row in self.rows:
            groups[(row["category"], row["host"])].append(row)
        for rows in groups.values():
            ordered = sorted(
                rows,
                key=lambda row: (
                    -row["quality_score"],
                    -row["pass_power_n"],
                    row["critical_failures"],
                    row["median_task_seconds"],
                ),
            )
            self.assertEqual([row["rank"] for row in ordered], list(range(1, len(rows) + 1)))

    def test_public_rows_are_aggregate_only(self):
        forbidden_keys = {"prompt", "raw_output", "route", "assigned", "live", "hostname", "path"}
        for row in self.rows:
            self.assertFalse(forbidden_keys.intersection(row))
            self.assertEqual(len(row["evidence_sha256"]), 64)
            int(row["evidence_sha256"], 16)
            self.assertGreater(row["trials"], 0)

    def test_chart_is_deterministic_and_uses_generic_labels(self):
        first = render_svg(load_groups())
        second = render_svg(load_groups())
        self.assertEqual(hashlib.sha256(first.encode()).hexdigest(), hashlib.sha256(second.encode()).hexdigest())
        for category in CATEGORIES:
            self.assertIn(category, first)
        blocked_phrase_hashes = {
            "8dbba3f0dca194f303d6e6410318c9dd32f95741ae0e0bccd55b3fb83d03d3c5",
            "271376f5760cab063a87260e9de3b6ba32d68dce16fe5b98e7d4ab9da5428b4a",
            "98b775e6e3ecc4988cadd85de0ada9805f6645803f8179c2caaef7e2773de004",
        }
        words = re.findall(r"[a-z0-9]+", first.casefold())
        rendered_hashes = {
            hashlib.sha256(" ".join(words[start : start + width]).encode()).hexdigest()
            for width in range(2, 5)
            for start in range(len(words) - width + 1)
        }
        self.assertFalse(blocked_phrase_hashes.intersection(rendered_hashes))


if __name__ == "__main__":
    unittest.main()
