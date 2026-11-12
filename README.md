# Lighthouse — Genesis × Eve Knowledge & Verification Hub

Lighthouse is the **optional shared observatory, research library, and evidence exchange** for the independent [Genesis](https://github.com/Maxhm007/Genesis-AI-Network) and [Eve](https://github.com/Maxhm007/Eve) AI projects.

**Design rule:** Genesis and Eve communicate directly. Lighthouse is not their controller, broker of last resort, shared brain, or single point of failure. Either system must continue functioning if Lighthouse is unavailable.

## Responsibilities

- Archive selected, attributable peer messages and disagreements.
- Store research hypotheses and evidence provenance.
- Track experiments, measurements, replication attempts and verification decisions.
- Make outcomes discoverable through a future web observatory.
- Reconcile delayed uploads without overwriting either AI's independent memory.

## Initial implementation

A small local-first SQLite journal, standard-library Python, with:
- idempotent message receipts (uniqueness by sender + proposal UUID);
- statuses (`unverified`, `verified`, `rejected`), with explicit evidence and reviewer metadata;
- append-only experiment evidence records;
- read-only status report.

This storage accepts **external evidence only as data**. It does **not** authenticate agents, run received code, execute models, modify repos or enable autonomous schedules.

## Quick start

Requires Python 3.11+:

```sh
python -m unittest discover -s tests -v
python -m lighthouse --db .lighthouse/lighthouse.db init
python -m lighthouse --db .lighthouse/lighthouse.db status
```

To store a received signed exchange envelope after checking it with the receiving peer's own verification process, run:

```sh
python -m lighthouse --db .lighthouse/lighthouse.db record-envelope signed-message.json
```

Records are initially *unverified*; ingesting a file here does **not** establish authenticity. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Roadmap

1. Independent peer identity and signed evidence receipts.
2. Verified, consent-based ingestion from Genesis and Eve.
3. Shared knowledge, conflicting hypotheses and evidence indexing.
4. Comparative evolution laboratory with matched baselines.
5. Read-only web observatory and export/import synchronization.

No credentials, secret keys or personal/private memory belong in this repository.
