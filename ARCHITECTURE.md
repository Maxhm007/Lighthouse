# Lighthouse Architecture v0.1

## Topology

```text
 Genesis  <------ direct authenticated peer link ------>  Eve
    |                                                     |
    | (optional, selected evidence)   (optional, selected evidence)
    +-------------------> Lighthouse <--------------------+
                  archive / verification / observatory
```

**Non-goals:** forcing all Genesis–Eve traffic through Lighthouse, central command, shared private memory, unlimited task execution, automatic cross-repository merges, or an authoritative arbitration AI.

## Boundaries

- Genesis and Eve retain independent identities, decisions, workflows, state, and memories.
- Lighthouse stores selected public or approved exchange records and immutable evidence.
- Incoming documents and messages are untrusted until an identity-aware verifier checks their signatures and provenance. A SHA-256 hash alone is not authentication.
- Messages are never interpreted as executable instructions.
- No remote network listener, model inference, scheduled tasks, GitHub tokens, or background synchronization in this foundation.
- Database defaults to an ignored local directory. Public repo contains source code and schema, not live private data.
- Human-reviewed promotion for verified conclusions; preserve rejected and conflicting hypotheses.

## Storage

SQLite is sufficient for the single-writer prototype; use WAL mode and transactions. PostgreSQL can be introduced if concurrent geographically distributed writers become necessary. Store content hashes, source identities, timestamps, evidence references and validation results.

## First scientific test

Compare (A) solo agent, (B) two collaborating agents with shared task context, (C) Genesis/Eve independent memory plus reciprocal critique. Fix tasks and resource budgets ahead of time. Track test success, novelty corroborated by independent tests, regressions, cost and repeatability.

## Future safety controls

- Public-key signatures with separately managed identity keys.
- Recipient-scoped access controls, rate limits, tamper-evident receipt history.
- Content redaction, evidence retention controls and backups.
- Replay-resistant protocol and signed verifiable dataset exports.
