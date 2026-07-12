import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from workman_field_tests.admission import validate_result


class AdmissionTests(unittest.TestCase):
    def fixture(self, scenario_path: Path):
        return {
            "schema_version": "workman-field-tests.v2",
            "runner_commit": "a" * 40,
            "scenario_sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
            "model": "fixture",
            "serving_artifact": "fixture",
            "model_revision": "revision",
            "runtime": "fixture-runtime",
            "runtime_version": "1.0",
            "hardware": "fixture-hardware",
            "hardware_memory_gb": 1,
            "os": "fixture-os",
            "quantization": "fixture",
            "context_limit": 4096,
            "sampling": {"temperature": 0, "top_p": 1, "seed": 0, "max_tokens": 10},
            "concurrency": 1,
            "no_think_controls": False,
            "created_utc": "2026-07-11T00:00:00Z",
            "summary": {"passed": 1, "total": 1, "pass_rate": 1, "latency_sample_n": 1},
            "rows": [{"scenario_id": "fixture", "passed": True}],
            "comparability_class": "quality/public-battery",
        }

    def test_valid_v2_result_passes_and_missing_field_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Path(temp) / "scenarios.json"
            scenario.write_text('{"scenarios":[]}', encoding="utf-8")
            data = self.fixture(scenario)
            self.assertEqual(validate_result(data, scenario), [])
            broken = copy.deepcopy(data)
            broken.pop("runtime_version")
            self.assertIn("missing:runtime_version", validate_result(broken, scenario))

    def test_scenario_hash_mismatch_and_privacy_leak_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Path(temp) / "scenarios.json"
            scenario.write_text('{"scenarios":[]}', encoding="utf-8")
            data = self.fixture(scenario)
            data["scenario_sha256"] = "b" * 64
            data["notes"] = "host=" + "192." + "168.1.4"
            issues = validate_result(data, scenario)
            self.assertIn("scenario_sha256_mismatch", issues)
            self.assertTrue(any(issue.startswith("privacy:") for issue in issues))


if __name__ == "__main__":
    unittest.main()
