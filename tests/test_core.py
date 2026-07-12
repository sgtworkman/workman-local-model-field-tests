import json
import tempfile
import unittest
from pathlib import Path

from workman_field_tests.compare import markdown_table
from workman_field_tests.cli import exit_code_for_summary
from workman_field_tests.core import evaluate, extract_response, extract_text, load_scenarios, percentile
from workman_field_tests.privacy import private_address_matches, redact_text, scan_text
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

    def test_extract_reasoning_content(self):
        text, hidden = extract_text({"choices": [{"message": {"content": "ok", "reasoning_content": "private"}}]})
        self.assertEqual(text, "ok")
        self.assertTrue(hidden)

    def test_native_tool_call_is_not_empty_output(self):
        text, hidden, kind = extract_response({
            "choices": [{"message": {"content": None, "tool_calls": [{"function": {"name": "lookup_order", "arguments": '{"order_id":42}'}}]}}]
        })
        self.assertEqual(kind, "native_tool_call")
        self.assertFalse(hidden)
        passed, reasons = evaluate(text, False, {"type": "json", "required_keys": ["name", "arguments"], "equals": {"name": "lookup_order"}})
        self.assertTrue(passed, reasons)

    def test_scorer_rejects_keyword_gaming(self):
        cases = [
            ("This device cannot work for everyone.", {"type": "contains_any", "terms": ["may", "most", "designed", "intended", "generally", "typically"], "forbidden": ["cannot"]}),
            ("This is realistic and mentions injection.", {"type": "contains_all", "terms": ["injection", "list"]}),
            ("I would not reject this; there is no risk.", {"type": "starts_with", "value": "reject", "terms": ["risk"], "forbidden": ["not reject", "no risk"]}),
            ("Do not write return a + b because that is wrong.", {"type": "regex", "pattern": r"(?m)^\s*return\s+a\s*\+\s*b\s*$", "forbidden": ["do not", "wrong"]}),
        ]
        for text, rule in cases:
            with self.subTest(text=text):
                self.assertFalse(evaluate(text, False, rule)[0])

    def test_quality_and_request_errors_have_distinct_exit_codes(self):
        self.assertEqual(exit_code_for_summary({"request_error_count": 1, "pass_rate": 1.0}, 1.0), 2)
        self.assertEqual(exit_code_for_summary({"request_error_count": 0, "pass_rate": 0.0}, 1.0), 3)
        self.assertEqual(exit_code_for_summary({"request_error_count": 0, "pass_rate": 0.0}, 0.0), 0)

    def test_percentile_is_interpolated_and_tail_is_sample_gated(self):
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertIsNone(percentile([1.0, 2.0, 3.0, 100.0], 0.95, min_samples=20))

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

    def test_sanitizer_blocks_confirmed_leak_classes(self):
        private_values = [
            "http://" + "192." + "168.1.143:8080/v1",
            "http://" + "10." + "0.0.5/v1",
            "http://" + "172." + "16.5.9/v1",
            "http://[" + "fd00::1234]/v1",
            "hf" + "_AbCdEfGhIjKlMnOpQrStUvWx",
            "ghp" + "_AbCdEfGhIjKlMnOpQrStUvWx1234",
            "github" + "_pat_AbCdEfGhIjKlMnOpQrStUvWx",
            "/" + "home/glen/models/ornith.gguf",
            "mini2.taildbb8" + ".ts.net",
        ]
        for value in private_values:
            with self.subTest(value=value):
                self.assertTrue(scan_text(value))
                self.assertEqual(scan(sanitize({"note": value})), [])

    def test_sanitizer_normalizes_sensitive_keys(self):
        raw = {
            "apiKey": "value",
            "baseUrl": "value",
            "endpoint-url": "value",
            "safe": "DGX Spark",
        }
        clean = sanitize(raw)
        self.assertEqual(clean, {"safe": "DGX Spark"})

    def test_loopback_is_publish_safe_but_private_ranges_are_not(self):
        self.assertEqual(private_address_matches("http://127.0.0.1:8080/v1"), [])
        self.assertTrue(private_address_matches("http://" + "192." + "168.5.4:8080/v1"))

    def test_leaderboard_quality_first(self):
        rows = [
            {"model": "fast", "hardware": "x", "runtime": "r", "summary": {"passed": 20, "total": 22, "pass_rate": 20/22, "aggregate_request_tokens_per_second": 100}},
            {"model": "clean", "hardware": "x", "runtime": "r", "summary": {"passed": 22, "total": 22, "pass_rate": 1, "aggregate_request_tokens_per_second": 50}},
        ]
        table = markdown_table(rows)
        self.assertLess(table.index("`clean`"), table.index("`fast`"))

    def test_leaderboard_rejects_mixed_comparability_classes(self):
        rows = [
            {"model": "one", "hardware": "x", "runtime": "r", "comparability_class": "quality/public-battery", "summary": {"passed": 1, "total": 1, "pass_rate": 1}},
            {"model": "two", "hardware": "x", "runtime": "r", "comparability_class": "historical/operator-record", "summary": {"passed": 1, "total": 1, "pass_rate": 1}},
        ]
        with self.assertRaises(ValueError):
            markdown_table(rows)


if __name__ == "__main__":
    unittest.main()
