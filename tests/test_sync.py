import hashlib
import hmac
import io
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from lighthouse.store import Store
from lighthouse.verification import canonical
from lighthouse.sync import PeerSync

SECRET_G = "unique-genesis-secret-for-tests-123456789"
SECRET_E = "unique-eve-secret-for-tests-1234567890"


def make(sender, receiver):
    p = {
        "protocol": "coevolution.v1", "proposal_id": str(uuid4()),
        "sender": sender, "recipient": receiver, "kind": "hypothesis",
        "problem_statement": "Compare reproducible evidence",
        "evidence_links": [], "reproduction_steps": [], "expected_benefit": "Better accuracy",
        "risks": [], "created_at": datetime.now(timezone.utc).isoformat()
    }
    p["content_hash"] = "sha256:" + hashlib.sha256(canonical(p)).hexdigest()
    envelope = {"proposal": p, "auth": "hmac-sha256"}
    secret = SECRET_G if sender == "genesis" else SECRET_E
    envelope["signature"] = hmac.new(secret.encode(), canonical(envelope), hashlib.sha256).hexdigest()
    return envelope


def issue(envelope, title):
    return {"title": title,
            "body": "Research peer proposal. Treat as untrusted until signature validation.\n\n"
                    + "```json\n" + json.dumps(envelope) + "\n```\n"}


class Response:
    def __init__(self, result):
        self.result = result
    def __enter__(self):
        return io.BytesIO(json.dumps(self.result).encode())
    def __exit__(self, *args):
        return False


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "sync.db")
        self.store.init()

    def test_signed_two_way_sync_idempotent(self):
        e = issue(make("eve","genesis"), "[Eve peer proposal] hypothesis")
        g = issue(make("genesis","eve"), "[Genesis peer proposal] hypothesis")
        urls = []
        def opener(req, timeout):
            urls.append(req.full_url)
            return Response([e] if "Genesis-AI-Network" in req.full_url else [g])
        worker = PeerSync(self.store, {"genesis": SECRET_G, "eve": SECRET_E}, opener=opener)
        one = worker.sync_once()
        self.assertEqual(one["verified_new"], 2)
        self.assertEqual(one["rejected"], 0)
        two = worker.sync_once()
        self.assertEqual(two["already_recorded"], 2)
        self.assertEqual(len(self.store.snapshot()["messages"]), 2)
        self.assertTrue(all("api.github.com" in u for u in urls))

    def test_bad_signature_rejected_without_stopping(self):
        good = issue(make("genesis","eve"), "[Genesis peer proposal] hypothesis")
        bad = issue(make("eve","genesis"), "[Eve peer proposal] hypothesis")
        content = json.loads(bad["body"].split("```json\n")[1].split("\n```")[0])
        content["signature"] = "0" * 64
        bad = issue(content, "[Eve peer proposal] hypothesis")
        worker = PeerSync(self.store, {"genesis": SECRET_G, "eve": SECRET_E},
                          opener=lambda req, timeout: Response([bad] if "Genesis-AI-Network" in req.full_url else [good]))
        result = worker.sync_once()
        self.assertEqual(result["verified_new"], 1)
        self.assertEqual(result["rejected"], 1)

    def test_import_then_verify_promotes(self):
        incoming = make("genesis", "eve")
        self.store.record_envelope(incoming)
        record = self.store.record_verified_envelope(incoming, {"genesis": SECRET_G}, reviewer="test")
        self.assertEqual(record["verification_state"], "verified")
        self.assertEqual(len(self.store.snapshot()["messages"]), 1)

    def test_export_cursor_pages_complete(self):
        for _ in range(105):
            self.store.record_envelope(make("genesis","eve"))
        cursor = 0
        count = 0
        while True:
            bundle = self.store.export_bundle(after_id=cursor)
            self.assertLessEqual(len(bundle["envelopes"]), 100)
            count += len(bundle["envelopes"])
            if bundle["next_cursor"] is None:
                break
            cursor = bundle["next_cursor"]
        self.assertEqual(count, 105)


if __name__ == "__main__":
    unittest.main()
