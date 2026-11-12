import json
import tempfile
import unittest
from pathlib import Path

from lighthouse.archive import SCHEMA, merge_receipts, run_sync


def row(sender, identifier, sha="a"*64):
    return {
        "sender": sender,
        "proposal_id": identifier,
        "sha256": sha,
        "reviewed_at": "2026-11-12T00:00:00+00:00",
    }


class ArchiveTests(unittest.TestCase):
    def test_repeat_sync_preserves_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "archive.json"
            def mocked_open(req, timeout):
                class Response:
                    def __enter__(self): return self
                    def __exit__(self, *args): return False
                    def read(self, size): return b"[]"
                return Response()
            secrets = {"genesis":"g"*32, "eve":"e"*32}
            one = run_sync(target, secrets, opener=mocked_open)
            two = run_sync(target, secrets, opener=mocked_open)
            self.assertEqual(one["archive_total"], 0)
            self.assertEqual(two["archive_added"], 0)
            self.assertEqual(json.loads(target.read_text())["schema"], SCHEMA)

    def test_existing_receipts_kept(self):
        old = {"schema": SCHEMA, "receipts": [row("genesis", "1")]}
        merged = merge_receipts(old, [row("eve", "2")])
        self.assertEqual(len(merged["receipts"]), 2)
        same = merge_receipts(merged, [row("eve", "2")])
        self.assertEqual(same, merged)

    def test_conflicting_payload_never_overwrites(self):
        old = {"schema": SCHEMA, "receipts": [row("genesis", "1")]}
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            merge_receipts(old, [row("genesis", "1", "b"*64)])

    def test_requires_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Missing"):
                run_sync(Path(tmp) / "receipts.json", {"genesis":"", "eve":""})

    def test_rejects_forged_archive_structure(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            merge_receipts({"schema": SCHEMA, "receipts": [{"admin":True}]}, [])


if __name__ == "__main__":
    unittest.main()
