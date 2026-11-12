import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from lighthouse.store import Store
from lighthouse.verification import canonical, verify_envelope
from lighthouse.observatory import render

GENESIS_KEY = "test-key-for-genesis-only-2026-abcdef1234"
EVE_KEY = "test-key-for-eve-only-2026-abcdefghij"


def message(sender="genesis"):
    p = {
        "protocol": "coevolution.v1", "proposal_id": str(uuid4()),
        "sender": sender, "recipient": "eve" if sender == "genesis" else "genesis",
        "kind": "hypothesis", "problem_statement": "Test independently",
        "evidence_links": [], "reproduction_steps": [],
        "expected_benefit": "Reproducibility", "risks": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    p["content_hash"] = "sha256:" + hashlib.sha256(canonical(p)).hexdigest()
    envelope = {"proposal": p, "auth": "hmac-sha256"}
    key = GENESIS_KEY if sender == "genesis" else EVE_KEY
    envelope["signature"] = hmac.new(key.encode(), canonical(envelope), hashlib.sha256).hexdigest()
    return envelope


class LighthouseV02(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "hub.db")
        self.store.init()

    def test_verified_ingest_and_stored_evidence(self):
        envelope = message()
        result = self.store.record_verified_envelope(envelope, {"genesis": GENESIS_KEY}, reviewer="test verifier")
        self.assertEqual(result["verification_state"], "verified")
        self.assertEqual(self.store.status()["messages"][0]["verification_state"], "verified")

    def test_wrong_key_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_verified_envelope(message(), {"genesis": EVE_KEY}, reviewer="test")
        self.assertEqual(self.store.status()["messages"], [])

    def test_replay_alternate_uuid_rejected(self):
        envelope = message()
        self.store.record_verified_envelope(envelope, {"genesis":GENESIS_KEY}, reviewer="test")
        with self.assertRaises(Exception):
            self.store.record_verified_envelope(envelope, {"genesis":GENESIS_KEY}, reviewer="test")

    def test_export_import_idempotent_and_unverified(self):
        self.store.record_envelope(message())
        packet = self.store.export_bundle()
        new = Store(Path(self.temp.name) / "import.db")
        new.init()
        self.assertEqual(new.import_bundle(packet)["imported"], 1)
        self.assertEqual(new.import_bundle(packet)["imported"], 0)
        self.assertEqual(new.status()["messages"][0]["verification_state"], "unverified")

    def test_observatory_escapes_untrusted_html(self):
        self.store.record_experiment("<script>alert(1)</script>", "joint", {"note":"test"})
        dest = Path(self.temp.name) / "observatory.html"
        render(self.store, dest)
        content = dest.read_text(encoding="utf-8")
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("Lighthouse Observatory", content)


if __name__ == "__main__":
    unittest.main()
