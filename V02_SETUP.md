# Lighthouse v0.2 — operator guide

Lighthouse is **optional**. Genesis and Eve communicate through their existing direct authenticated link; Lighthouse cannot block or control them.

Python 3.11+, no web service or third-party packages.

## Local dashboard

```sh
python -m lighthouse --db .lighthouse/lighthouse.db init
python -m lighthouse --db .lighthouse/lighthouse.db observatory .lighthouse/observatory.html
```

Open the generated HTML in a browser. The page is static, read-only and escapes untrusted fields. It does not connect to GitHub or expose the SQLite database online.

## Signed receipt

Lighthouse can verify existing `coevolution.v1` **HMAC** envelopes, compatible with the Genesis and Eve pilots. Configure keys locally as `LIGHTHOUSE_GENESIS_SECRET` and `LIGHTHOUSE_EVE_SECRET`, then run:

```sh
python -m lighthouse --db .lighthouse/lighthouse.db verify-envelope signed-message.json --reviewer local-operator
```

A *verified* status means only that the envelope and signature matched the configured secret, **not** that the scientific claim was established. A shared HMAC key does **not** establish a unique independent AI identity; both holders could impersonate each other. For agent-specific attribution, configure distinct per-sender keys and update the sending peers accordingly. Never commit keys.

## Offline recovery

```sh
python -m lighthouse --db .lighthouse/lighthouse.db export .lighthouse/exchange.json
# When next_cursor is non-null, repeat with --cursor NEXT_CURSOR and a new filename
python -m lighthouse --db .lighthouse/recovery.db import .lighthouse/exchange.json
```

Imported messages always start *unverified*, even if verified in the source database. Re-verify by signature before using them. Re-importing the same IDs will not create duplicates.

**Privacy warning:** export contains complete stored message envelopes, potentially including sensitive research text and references. Inspect and redact before sharing. Do not commit the export, database, or HTML report containing sensitive content.

## Not yet operational

- True asymmetric per-agent signatures
- Automatic sync and authenticated live network service
- Distributed database replication
- AI-generated conversation or autonomous evolution
- Hosted/public web observatory

See [issue #1](https://github.com/Maxhm007/Lighthouse/issues/1) for future milestones.

## Opt-in verified GitHub issue synchronization

Configure the two peer signing secrets locally as `LIGHTHOUSE_GENESIS_SECRET` and `LIGHTHOUSE_EVE_SECRET`, ensuring that they match the keys used for messages signed by the respective peer. Set `LIGHTHOUSE_GITHUB_READ_TOKEN` only if needed for private repositories or to increase GitHub API rate limits; it requires read-only Issues access. Then run:

```sh
python -m lighthouse --db .lighthouse/lighthouse.db sync-once --pages 1
python -m lighthouse --db .lighthouse/lighthouse.db observatory .lighthouse/observatory.html
```

The sync command **reads** recent issues from both peer repositories, checks a strict signed-envelope format, verifies source/destination and HMAC, and stores signed receipts. Running it repeatedly is idempotent. It does not send messages, ask models to reason, modify issues, or control Genesis/Eve. Without correctly configured secrets it records no verified messages. The two simulated pilot issues (Genesis#1169 and Eve#3) deliberately lack signatures and are not treated as trusted peer exchanges.

For periodic operation on your own machine, run `sync-once` from Windows Task Scheduler or cron with access to a persistent local SQLite database and the required secrets. No schedule has been enabled by this project. A GitHub Actions runner is intentionally unsuitable for the SQLite journal unless a separate persistent storage service is configured.

With legacy shared HMAC secrets, cryptographic verification proves only that the key holder signed the message. Genuine independent AI attribution still requires separate identities and asymmetric signatures. **Verified does not mean a research claim is scientifically true.**
