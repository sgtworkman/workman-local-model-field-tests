from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


B12X_SUPPORTED_ACTIVATIONS = frozenset({"relu2", "silu", "swiglu"})


def evaluate_memory_reservation(
    *,
    free_gib: float,
    total_gib: float,
    host_available_gib: float,
    gpu_memory_utilization: float,
    gpu_headroom_gib: float = 0.0,
    host_headroom_gib: float = 8.0,
) -> dict[str, Any]:
    """Fail closed when a unified-memory launch cannot preserve both margins."""
    values = (
        free_gib,
        total_gib,
        host_available_gib,
        gpu_memory_utilization,
        gpu_headroom_gib,
        host_headroom_gib,
    )
    valid = all(math.isfinite(value) for value in values) and all(
        (
            free_gib >= 0,
            total_gib > 0,
            host_available_gib >= 0,
            0 < gpu_memory_utilization <= 1,
            gpu_headroom_gib >= 0,
            host_headroom_gib >= 0,
        )
    )
    reservation_gib = total_gib * gpu_memory_utilization if valid else None
    gpu_required_gib = reservation_gib + gpu_headroom_gib if reservation_gib is not None else None
    host_required_gib = reservation_gib + host_headroom_gib if reservation_gib is not None else None
    gpu_margin_gib = free_gib - gpu_required_gib if gpu_required_gib is not None else None
    host_margin_gib = host_available_gib - host_required_gib if host_required_gib is not None else None

    if not valid:
        reason = "invalid_memory_input"
    elif gpu_margin_gib is not None and gpu_margin_gib < 0:
        reason = "reservation_exceeds_free_memory"
    elif host_margin_gib is not None and host_margin_gib < 0:
        reason = "reservation_exceeds_host_available_memory"
    else:
        reason = None
    passed = reason is None
    return {
        "status": "PASS" if passed else "FAIL_CLOSED",
        "reason": reason,
        "reservation_gib": reservation_gib,
        "gpu_required_gib": gpu_required_gib,
        "host_required_gib": host_required_gib,
        "gpu_margin_gib": gpu_margin_gib,
        "host_margin_gib": host_margin_gib,
    }


def evaluate_backend(*, backend: str, activation: str | None) -> dict[str, Any]:
    """Validate explicitly forced inference backends against a narrow policy."""
    normalized_backend = backend.strip().lower()
    normalized_activation = activation.strip().lower() if isinstance(activation, str) and activation.strip() else None
    if normalized_backend == "auto":
        return {
            "status": "PASS",
            "backend": normalized_backend,
            "activation": normalized_activation,
            "reason": "runtime_selects_supported_backend",
        }
    if normalized_backend in {"b12x", "flashinfer_b12x"}:
        passed = normalized_activation in B12X_SUPPORTED_ACTIVATIONS
        return {
            "status": "PASS" if passed else "FAIL_CLOSED",
            "backend": normalized_backend,
            "activation": normalized_activation,
            "reason": None if passed else "forced_b12x_activation_not_proven_supported",
            "supported_activations": sorted(B12X_SUPPORTED_ACTIVATIONS),
        }
    return {
        "status": "FAIL_CLOSED",
        "backend": normalized_backend,
        "activation": normalized_activation,
        "reason": "forced_backend_not_in_verified_policy",
    }


def evaluate_adapter_profiles(probes: list[dict[str, Any]]) -> bool:
    """Admit a thinking model only when both controlled adapters are clean.

    The uncontrolled profile is a route diagnostic. It may expose reasoning or
    exhaust a small output budget without invalidating clean no-think profiles.
    """
    by_name = {probe.get("profile"): probe for probe in probes}
    diagnostic = by_name.get("openai_default")
    controlled = (
        by_name.get("openai_no_think_controls"),
        by_name.get("openai_json_schema_controls"),
    )
    diagnostic_ok = bool(
        diagnostic
        and diagnostic.get("http_status") == 200
        and diagnostic.get("route_ok") is True
    )
    controlled_ok = all(
        probe
        and probe.get("http_status") == 200
        and probe.get("non_empty") is True
        and probe.get("route_ok") is True
        and probe.get("reasoning_leak") is not True
        for probe in controlled
    )
    return diagnostic_ok and controlled_ok


def load_module_from_path(name: str, path: str | Path) -> ModuleType:
    """Load a file-backed scorer while making sibling imports resolvable."""
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    parent = str(source.parent)
    added = parent not in sys.path
    if added:
        sys.path.insert(0, parent)
    try:
        spec = importlib.util.spec_from_file_location(name, source)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load module spec: {source}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if added and sys.path and sys.path[0] == parent:
            sys.path.pop(0)
