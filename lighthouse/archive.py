"""Persist only signed-message receipts, never peer content or credentials.

A GitHub Actions job uses this script with a git-backed JSON file to carry
idempotent verification history across short-lived runners.
"""
import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from .store import Store
from .sync import PeerSync

SCHEMA = "lighthouse-public-receipts-v1"
MAX_RECEIPTS = 50000


def validate_history(data):
    if not isinstance(data, dict) or set(data) != {"schema", "receipts"} or data["schema"] != SCHEMA:
        raise ValueError("Invalid receipts archive")
    entries = data["receipts"]
    if not isinstance(entries, list) or len(entries) > MAX_RECEIPTS:
        raise ValueError("Invalid archive size")
    seen = set()
    for receipt in entries:
        if not isinstance(receipt, dict) or set(receipt) != {"sender","proposal_id","sha256","reviewed_at"}:
            raise ValueError("Invalid archived receipt")
        if receipt["sender"] not in ("genesis", "eve"):
            raise ValueError("Invalid sender")
        if not all(isinstance(receipt[k], str) and 0 < len(receipt[k]) <= 128
                   for k in ("proposal_id", "sha256", "reviewed_at")):
            raise ValueError("Invalid receipt fields")
        key = (receipt["sender"], receipt["proposal_id"])
        if key in seen:
            raise ValueError("Duplicate archive identifier")
        seen.add(key)
    return entries


def merge_receipts(old, fresh):
    """Reject conflicting hashes, retain historical rows, and sort deterministically."""
    existing = {(r["sender"], r["proposal_id"]): r for r in validate_history(old)}
    for row in fresh:
        key = (row["sender"], row["proposal_id"])
        previous = existing.get(key)
        if previous:
            if previous["sha256"] != row["sha256"]:
                raise ValueError("Conflicting signed receipt for existing ID")
        else:
            existing[key] = row
    if len(existing) > MAX_RECEIPTS:
        raise ValueError("Archive capacity exceeded")
    return {"schema": SCHEMA, "receipts": [
        existing[key] for key in sorted(existing)
    ]}


def run_sync(archive, secrets, opener=None, pages=1):
    if not all(isinstance(secrets.get(k), str) and len(secrets[k]) >= 32 for k in ("genesis", "eve")):
        raise ValueError("Missing Genesis or Eve verification secret")
    with tempfile.TemporaryDirectory() as temp:
        db = Store(Path(temp) / "lighthouse.db")
        db.init()
        result = PeerSync(db, secrets, opener=opener).sync_once(pages=pages)
        with db.connect() as conn:
            fresh = [dict(row) for row in conn.execute("""
                SELECT sender,proposal_id,sha256,reviewed_at FROM messages
                WHERE verification_state='verified'
                ORDER BY sender,proposal_id
            """)]
    old = json.loads(Path(archive).read_text(encoding="utf-8")) if Path(archive).exists() else {
        "schema": SCHEMA, "receipts": []
    }
    merged = merge_receipts(old, fresh)
    original = len(old["receipts"])
    target = Path(archive)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**result, "archive_total": len(merged["receipts"]),
            "archive_added": len(merged["receipts"]) - original}


def main():
    parser = argparse.ArgumentParser(description="One-shot persistent Lighthouse sync")
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()
    result = run_sync(args.archive, {
        "genesis": os.getenv("LIGHTHOUSE_GENESIS_SECRET", ""),
        "eve": os.getenv("LIGHTHOUSE_EVE_SECRET", ""),
    }, pages=args.pages)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
