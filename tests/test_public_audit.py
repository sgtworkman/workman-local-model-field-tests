import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_public_repo import (
    audit_files,
    changed_worktree_paths,
    internal_label_findings,
    tracked_files,
)


class PublicAuditTests(unittest.TestCase):
    def test_release_audit_includes_untracked_candidates(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            path = Path(temp) / "new-public-candidate.txt"
            path.write_text("safe fixture", encoding="utf-8")
            self.assertIn(path, tracked_files())

    def test_private_network_fixtures_fail_boundary_audit(self):
        fixture_text = "\n".join(
            [
                "address=" + "192." + "168.1.4",
                "address=" + "10." + "0.0.8",
                "address=" + "172." + "31.4.9",
                "address=[" + "fd00::9]",
            ]
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.txt"
            path.write_text(fixture_text, encoding="utf-8")
            findings = audit_files([path])
        self.assertEqual(len(findings), 4)

    def test_binary_release_assets_are_skipped_without_decoding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "chart.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 1024)
            self.assertEqual(audit_files([path]), [])

    def test_untracked_release_candidates_are_worktree_changes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temp:
            path = Path(temp) / "candidate.txt"
            path.write_text("safe fixture", encoding="utf-8")
            changed_worktree_paths.cache_clear()
            self.assertIn(str(path.relative_to(Path(__file__).resolve().parents[1])), changed_worktree_paths())

    def test_hashed_internal_lane_label_fails_public_audit(self):
        private_label = "private lane"
        digest = hashlib.sha256(private_label.encode("utf-8")).hexdigest()
        findings = internal_label_findings(
            "This mentions the Private Lane in public copy.",
            {digest: "Public Workflow"},
        )
        self.assertEqual(findings, [f"internal_label_hash:{digest};use=Public Workflow"])


if __name__ == "__main__":
    unittest.main()
