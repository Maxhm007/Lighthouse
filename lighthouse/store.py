"""Local-only SQLite journal for selected peer exchange evidence.

Ingestion NEVER implies authentication or verification; all inputs start
unverified. No message content is executed or used as a privileged command.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from .verification import verify_envelope


def _now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def init(self):
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL CHECK(sender IN ('genesis','eve')),
                    recipient TEXT NOT NULL CHECK(recipient IN ('genesis','eve')),
                    proposal_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    verification_state TEXT NOT NULL DEFAULT 'unverified'
                        CHECK(verification_state IN ('unverified','verified','rejected')),
                    received_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewer TEXT,
                    review_evidence TEXT,
                    UNIQUE(sender, proposal_id)
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def record_envelope(self, envelope):
        if not isinstance(envelope, dict) or set(envelope) != {'proposal','auth','signature'}:
            raise ValueError("Invalid envelope shape")
        proposal = envelope['proposal']
        if not isinstance(proposal, dict) or proposal.get('sender') not in {'genesis','eve'} or proposal.get('recipient') not in {'genesis','eve'}:
            raise ValueError("Invalid peer")
        if proposal['sender'] == proposal['recipient']:
            raise ValueError("Peer must differ")
        proposal_id = str(UUID(proposal['proposal_id']))
        kind = proposal.get('kind')
        if kind not in {'hypothesis','test','critique','candidate_patch'}:
            raise ValueError("Invalid kind")
        raw = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        if len(raw.encode()) > 40000:
            raise ValueError("Envelope too large")
        content_hash = hashlib.sha256(raw.encode()).hexdigest()
        row_id = str(uuid4())
        with self.connect() as db:
            db.execute("""
                INSERT INTO messages (id,sender,recipient,proposal_id,kind,envelope_json,sha256,received_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (row_id, proposal['sender'], proposal['recipient'], proposal_id, kind, raw, content_hash, _now()))
        return {'id': row_id, 'sha256': content_hash, 'verification_state': 'unverified'}

    def record_experiment(self, title, source, evidence):
        if not isinstance(title, str) or not title.strip() or len(title) > 300:
            raise ValueError('Invalid title')
        if source not in {'genesis','eve','joint','external'}:
            raise ValueError('Invalid source')
        raw = json.dumps(evidence, ensure_ascii=False)
        if len(raw.encode()) > 100000:
            raise ValueError('Evidence too large')
        row_id = str(uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO experiments VALUES (?,?,?,?,?)', (row_id,title,source,raw,_now()))
        return row_id

    def status(self):
        with self.connect() as db:
            messages = [dict(r) for r in db.execute('SELECT verification_state,COUNT(*) AS count FROM messages GROUP BY verification_state')]
            experiments = db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]
        return {'messages': messages, 'experiments': experiments}

    def record_verified_envelope(self, envelope, sender_secrets, reviewer):
        """Verify full payload before insertion, then persist the verified receipt.

        This marks *signature verification*, not independent factual validation.
        """
        receipt = verify_envelope(envelope, sender_secrets)
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 160:
            raise ValueError("Verifier identity required")
        proposal = envelope["proposal"]
        raw = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record_id = str(uuid4())
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with self.connect() as db:
            existing = db.execute(
                "SELECT id,sha256,verification_state FROM messages WHERE sender=? AND proposal_id=?",
                (receipt["sender"], receipt["proposal_id"])
            ).fetchone()
            if existing:
                if existing["sha256"] != digest:
                    raise ValueError("Conflicting payload for existing proposal ID")
                if existing["verification_state"] == "rejected":
                    raise ValueError("Rejected item cannot be implicitly promoted")
                db.execute("""
                    UPDATE messages SET verification_state='verified', reviewed_at=?,
                    reviewer=?, review_evidence=? WHERE id=? AND verification_state='unverified'
                """, (receipt["verified_at"], reviewer,
                      "Signature verified; scientific claims unreviewed", existing["id"]))
                record_id = existing["id"]
            else:
                db.execute("""
                    INSERT INTO messages
                    (id,sender,recipient,proposal_id,kind,envelope_json,sha256,
                     verification_state,received_at,reviewed_at,reviewer,review_evidence)
                    VALUES (?,?,?,?,?,?,?,'verified',?,?,?,?)
                """, (record_id, receipt["sender"], proposal["recipient"], receipt["proposal_id"],
                      proposal["kind"], raw, digest, _now(), receipt["verified_at"], reviewer,
                      "Signature verified; scientific claims unreviewed"))
        return {"id": record_id, "verification_state": "verified", "sha256": digest}

    def snapshot(self):
        with self.connect() as db:
            messages = [dict(r) for r in db.execute("""
                SELECT sender,recipient,kind,verification_state,received_at
                FROM messages ORDER BY received_at DESC LIMIT 500
            """)]
            experiments = [dict(r) for r in db.execute("""
                SELECT title,source,created_at FROM experiments ORDER BY created_at DESC LIMIT 500
            """)]
            counts = [dict(r) for r in db.execute("""
                SELECT verification_state, COUNT(*) count FROM messages GROUP BY verification_state
            """)]
        return {"messages": messages, "experiments": experiments, "messages_by_state": counts}

    def export_bundle(self):
        """Portable, public-data-only export. Verification statuses NEVER transfer as trust."""
        with self.connect() as db:
            envelopes = [json.loads(r[0]) for r in db.execute(
                "SELECT envelope_json FROM messages ORDER BY received_at LIMIT 5000")]
        return {"format": "lighthouse-exchange-v1", "envelopes": envelopes}

    def import_bundle(self, bundle):
        """Idempotent, bounded offline import. Every imported message is unverified."""
        if not isinstance(bundle, dict) or set(bundle) != {"format","envelopes"} or bundle["format"] != "lighthouse-exchange-v1":
            raise ValueError("Invalid bundle format")
        envelopes = bundle["envelopes"]
        if not isinstance(envelopes, list) or len(envelopes) > 1000:
            raise ValueError("Invalid bundle size")
        if len(json.dumps(bundle, ensure_ascii=False).encode()) > 5_000_000:
            raise ValueError("Oversized bundle")
        imported, duplicates = 0, 0
        for envelope in envelopes:
            try:
                self.record_envelope(envelope)
                imported += 1
            except sqlite3.IntegrityError:
                duplicates += 1
        return {"imported": imported, "duplicates": duplicates}
