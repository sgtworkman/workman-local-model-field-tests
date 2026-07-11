import json
import tempfile
import unittest
from pathlib import Path

from workman_field_tests.compare import markdown_table
from workman_field_tests.core import evaluate, extract_text, load_scenarios
from workman_field_tests.sanitize import sanitize, scan


class CoreTests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(evaluate("FIELD_TEST_OK", False, {"type": "exact", "value": "FIELD_TEST_OK"}), (True, []))

    def test_reasoning_leak_fails(self):
        passed, reasons = evaluate("<think>x</think> FIELD_TEST_OK", False, {"type": "contains_all", "terms": ["FIELD_TEST_OK"]})
        self.assertFalse(passed)
        self.assertIn("reasoning_leak", reasons)

    def test_json_shape(self):
        passed, reasons = evaluate('{"name":"lookup_order","arguments":{"order_id":42}}', False, {"type": "json", "required_keys": ["name", "arguments"], "equals": {"name": "lookup_order"}})
        self.assertTrue(passed, reasons)

    def test_code_fence_is_valid_for_code_but_not_json(self):
        code_passed, _ = evaluate("```python\nreturn a + b\n```", False, {"type": "contains_all", "terms": ["return a + b"]})
        json_passed, reasons = evaluate("```json\n{}\n```", False, {"type": "json", "required_keys": []})
        self.assertTrue(code_passed)
        self.assertFalse(json_passed)
        self.assertIn("markdown_fence", reasons)

    def test_contains_any(self):
        passed, reasons = evaluate("Works well for most users.", False, {"type": "contains_any", "terms": ["may", "most"]})
        self.assertTrue(passed, reasons)

    def test_extract_hidden_reasoning(self):
        text, hidden = extract_text({"choices": [{"message": {"content": "ok", "reasoning": "private"}}]})
        self.assertEqual(text, "ok")
        self.assertTrue(hidden)

    def test_public_battery_has_11_scenarios(self):
        path = Path(__file__).resolve().parents[1] / "scenarios" / "public-22-check.json"
        self.assertEqual(len(load_scenarios(path)), 11)

    def test_sanitizer(self):
        raw = {
            "base_url": "http://" + "100." + "64.0.1:8000/v1",
            "note": "/" + "Users/alice/private",
            "token": "secret",
            "safe": "DGX Spark",
        }
        clean = sanitize(raw)
        self.assertNotIn("base_url", clean)
        self.assertNotIn("token", clean)
        self.assertEqual(clean["safe"], "DGX Spark")
        self.assertEqual(scan(clean), [])

    def test_leaderboard_quality_first(self):
        rows = [
            {"model": "fast", "hardware": "x", "runtime": "r", "summary": {"passed": 20, "total": 22, "pass_rate": 20/22, "median_generation_tokens_per_second": 100}},
            {"model": "clean", "hardware": "x", "runtime": "r", "summary": {"passed": 22, "total": 22, "pass_rate": 1, "median_generation_tokens_per_second": 50}},
        ]
        table = markdown_table(rows)
        self.assertLess(table.index("`clean`"), table.index("`fast`"))


if __name__ == "__main__":
    unittest.main()
