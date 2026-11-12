"""Opt-in HMAC verification compatible with Genesis/Eve coevolution.v1.

Security: separate per-sender secrets. Legacy shared-key envelopes are only
cryptographically attributable to the key holder, NOT independently to an AI.
Do not feed message text to execution tools.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

FIELDS = {"protocol","proposal_id","sender","recipient","kind","problem_statement",
          "evidence_links","reproduction_steps","expected_benefit","risks",
          "content_hash","created_at"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def verify_envelope(envelope, sender_secrets, now=None):
    if not isinstance(envelope, dict) or set(envelope) != {"proposal","auth","signature"}:
        raise ValueError("Invalid signed envelope")
    if envelope["auth"] != "hmac-sha256" or len(canonical(envelope)) > 40000:
        raise ValueError("Unsupported authentication or oversized payload")
    p = envelope["proposal"]
    if not isinstance(p, dict) or set(p) != FIELDS:
        raise ValueError("Invalid proposal schema")
    sender, receiver = p["sender"], p["recipient"]
    if sender not in {"genesis","eve"} or receiver not in {"genesis","eve"} or sender == receiver:
        raise ValueError("Invalid sender or recipient")
    if p["protocol"] != "coevolution.v1" or p["kind"] not in {"hypothesis","test","critique","candidate_patch"}:
        raise ValueError("Invalid proposal protocol or kind")
    UUID(p["proposal_id"])
    if not all(isinstance(p[k], str) and p[k].strip() and len(p[k]) <= 8000
               for k in ("problem_statement","expected_benefit")):
        raise ValueError("Invalid content")
    if not all(isinstance(p[k], list) and len(p[k]) <= 30 and
               all(isinstance(v, str) and len(v) <= 2048 for v in p[k])
               for k in ("evidence_links","reproduction_steps","risks")):
        raise ValueError("Invalid evidence fields")
    timestamp = datetime.fromisoformat(p["created_at"].replace("Z","+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Timezone required")
    now = now or datetime.now(timezone.utc)
    if timestamp < now - timedelta(days=7) or timestamp > now + timedelta(minutes=5):
        raise ValueError("Stale or future message")
    unsigned = dict(p)
    digest = unsigned.pop("content_hash")
    expected_digest = "sha256:" + hashlib.sha256(canonical(unsigned)).hexdigest()
    if not isinstance(digest, str) or not hmac.compare_digest(digest, expected_digest):
        raise ValueError("Content hash mismatch")
    secret = sender_secrets.get(sender, "")
    if not isinstance(secret, str) or len(secret) < 32:
        raise ValueError("Sender key unavailable")
    expected = hmac.new(secret.encode(), canonical({"proposal":p,"auth":"hmac-sha256"}), hashlib.sha256).hexdigest()
    if not isinstance(envelope["signature"], str) or not hmac.compare_digest(expected, envelope["signature"]):
        raise ValueError("Signature mismatch")
    return {"sender": sender, "proposal_id": str(UUID(p["proposal_id"])),
            "verifier": "hmac-sha256", "verified_at": now.isoformat()}
