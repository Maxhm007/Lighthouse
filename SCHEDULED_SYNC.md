# Lighthouse scheduled synchronization (GitHub Actions)

## What was built

- A scheduled workflow at `02:17` and `14:17 UTC` (08:17 and 20:17 Bangladesh time), plus manual dispatch.
- A separate branch `lighthouse-sync-state` holds only **minimal verified receipts**, not full message bodies or secrets.
- Each run checks peer issues, cryptographically verifies properly signed `coevolution.v1` messages, deduplicates receipts, and commits a changed archive only if needed.
- Both Genesis and Eve remain independently operational if Lighthouse is offline. Lighthouse does not execute incoming messages or write to those repositories.
- `GITHUB_TOKEN` is limited to contents permission in the **Lighthouse** repository. Optional `LIGHTHOUSE_GITHUB_READ_TOKEN` is for read-only access to external peer issues.

## Required one-time setup

In **Lighthouse → Settings → Secrets and variables → Actions**, configure:

- `LIGHTHOUSE_GENESIS_SECRET`: the same 32+ character HMAC secret Genesis uses to sign outbound peer messages.
- `LIGHTHOUSE_EVE_SECRET`: the same 32+ character HMAC secret Eve uses to sign outbound peer messages.
- `LIGHTHOUSE_GITHUB_READ_TOKEN` (optional): narrowly scoped read-only Issues token for the other repositories, if necessary.

**Do not generate unrelated Lighthouse keys.** If they do not match the peer senders, messages will not authenticate. The earlier Genesis/Eve pilot used a shared secret; in that legacy setup both names may need the same secret. That allows either holder to impersonate the other, so replace it with independently owned asymmetric signatures before relying on strong identity guarantees.

GitHub Apps or repository secrets cannot be provisioned by this source-code commit. The workflow checks for missing keys and **fails clearly instead of claiming it synchronized anything**.

## Runtime state

The verified receipt metadata is stored on [the lighthouse-sync-state branch](https://github.com/Maxhm007/Lighthouse/tree/lighthouse-sync-state) at `.lighthouse-sync/receipts.json`. Public records contain sender, proposal UUID, signature-envelope SHA-256 and verification timestamp. There are no model prompts, complete messages or private memories in this branch.

The stateless runner builds a fresh SQLite database, verifies selected public issue messages, merges receipt metadata with the archived state, and pushes only new records to the state branch. The workflow does not pretend that ephemeral GitHub Actions SQLite files persist between runs.

## Operational limitations

- With no signed outbound Genesis/Eve messages, the verified archive will stay empty.
- Existing manual handshake issues were not signed and are intentionally ignored.
- Polling is bounded to ten pages (up to 1,000 issues per repository) per run. Very old records outside the window require a separate backfill.
- The workflow can fail due to repository branch protections or exhausted Actions quota. Check its execution results.
- The workflow runs on a schedule only after it is merged into the default branch, and GitHub scheduling may be delayed.
- This is automated **Lighthouse archival**, not autonomous Genesis–Eve evolution, model deployment, or authenticated real-time two-way conversations.
- It provides no scientific verification of peer claims: 'verified' means a correctly signed envelope from a holder of the configured key.

## Diagnostics

Run `python -m unittest discover -s tests -v` in the repo. Under **Actions → Lighthouse scheduled peer sync**, launch `Run workflow` and inspect the step summary. If the secret verification step fails, provision the peer secrets before expecting archival. To view the current public receipt record, visit the state branch.

To use free CPU-only AI locally, see [Eve model setup](https://github.com/Maxhm007/Eve/blob/main/MODEL_SETUP.md).
