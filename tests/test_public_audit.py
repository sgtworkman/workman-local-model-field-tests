import tempfile
import unittest
from pathlib import Path

from scripts.audit_public_repo import audit_files, tracked_files


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


if __name__ == "__main__":
    unittest.main()
