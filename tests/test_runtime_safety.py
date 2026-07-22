import tempfile
import unittest
from pathlib import Path

from workman_field_tests.runtime_safety import (
    evaluate_adapter_profiles,
    evaluate_backend,
    evaluate_memory_reservation,
    load_module_from_path,
)


class RuntimeSafetyTests(unittest.TestCase):
    def adapter_probe(self, profile, *, route_ok=True, non_empty=True, reasoning_leak=False):
        return {
            "profile": profile,
            "http_status": 200,
            "route_ok": route_ok,
            "non_empty": non_empty,
            "reasoning_leak": reasoning_leak,
        }

    def test_unified_memory_pressure_fails_closed(self):
        result = evaluate_memory_reservation(
            free_gib=94.01,
            total_gib=121.69,
            host_available_gib=64.82,
            gpu_memory_utilization=0.68,
            gpu_headroom_gib=1,
        )
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason"], "reservation_exceeds_host_available_memory")

    def test_lower_reservation_preserves_unified_memory_headroom(self):
        result = evaluate_memory_reservation(
            free_gib=70.01,
            total_gib=121.69,
            host_available_gib=74.94,
            gpu_memory_utilization=0.45,
            gpu_headroom_gib=1,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["host_margin_gib"], 0)

    def test_invalid_memory_input_fails_closed(self):
        result = evaluate_memory_reservation(
            free_gib=100,
            total_gib=121,
            host_available_gib=100,
            gpu_memory_utilization=1.1,
        )
        self.assertEqual(result["reason"], "invalid_memory_input")

    def test_auto_backend_passes(self):
        self.assertEqual(evaluate_backend(backend="auto", activation="gelu_tanh")["status"], "PASS")

    def test_forced_b12x_requires_supported_activation(self):
        self.assertEqual(evaluate_backend(backend="flashinfer_b12x", activation="gelu_tanh")["status"], "FAIL_CLOSED")
        self.assertEqual(evaluate_backend(backend="flashinfer_b12x", activation="silu")["status"], "PASS")

    def test_unknown_forced_backend_fails_closed(self):
        self.assertEqual(evaluate_backend(backend="unknown", activation="silu")["status"], "FAIL_CLOSED")

    def test_default_thinking_is_diagnostic_when_controls_are_clean(self):
        probes = [
            self.adapter_probe("openai_default", non_empty=False, reasoning_leak=True),
            self.adapter_probe("openai_no_think_controls"),
            self.adapter_probe("openai_json_schema_controls"),
        ]
        self.assertTrue(evaluate_adapter_profiles(probes))

    def test_controlled_reasoning_leak_fails(self):
        probes = [
            self.adapter_probe("openai_default"),
            self.adapter_probe("openai_no_think_controls", reasoning_leak=True),
            self.adapter_probe("openai_json_schema_controls"),
        ]
        self.assertFalse(evaluate_adapter_profiles(probes))

    def test_wrong_route_and_missing_controlled_profile_fail(self):
        wrong_route = [
            self.adapter_probe("openai_default", route_ok=False),
            self.adapter_probe("openai_no_think_controls"),
            self.adapter_probe("openai_json_schema_controls"),
        ]
        missing = [
            self.adapter_probe("openai_default"),
            self.adapter_probe("openai_no_think_controls"),
        ]
        self.assertFalse(evaluate_adapter_profiles(wrong_route))
        self.assertFalse(evaluate_adapter_profiles(missing))

    def test_file_backed_module_can_import_sibling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sibling.py").write_text("VALUE = 42\n", encoding="utf-8")
            target = root / "target.py"
            target.write_text("from sibling import VALUE\nRESULT = VALUE\n", encoding="utf-8")
            self.assertEqual(load_module_from_path("temporary_target", target).RESULT, 42)

    def test_missing_module_fails(self):
        with self.assertRaises(FileNotFoundError):
            load_module_from_path("missing", "/definitely/not/here.py")


if __name__ == "__main__":
    unittest.main()
