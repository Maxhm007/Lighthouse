"""Opt-in one-shot read-only GitHub issue synchronization.

Only whitelisted peer repositories are queried. Incoming message content is
untrusted until independently HMAC-verified. No token writes, agent commands,
scheduled background loops, or cross-repository modifications.
"""
import json
import os
import re
import urllib.request

from .verification import verify_envelope

REPOS = {
    "genesis": "Maxhm007/Genesis-AI-Network",
    "eve": "Maxhm007/Eve",
}
PREFIX = "Research peer proposal. Treat as untrusted until signature validation."
CODE_PATTERN = re.compile(
    r"^Research peer proposal\. Treat as untrusted until signature validation\.\s+"
    r"```json\s*([\s\S]*?)\s*```\s*$"
)
MAX_PAYLOAD = 1_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect denied")


def default_open(request, timeout=30):
    return urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout)


class PeerSync:
    def __init__(self, store, secrets, token=None, opener=None):
        self.store = store
        self.secrets = secrets
        self.token = token if token is not None else os.getenv("LIGHTHOUSE_GITHUB_READ_TOKEN", "")
        self.opener = opener or default_open

    def _fetch_issues(self, repo, page):
        if repo not in REPOS or not 1 <= page <= 10:
            raise ValueError("Unapproved peer or page")
        endpoint = "https://api.github.com/repos/{}/issues?state=all&per_page=100&page={}".format(
            REPOS[repo], page)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Lighthouse-ReadOnly-Sync/0.2",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(endpoint, headers=headers, method="GET")
        with self.opener(request, timeout=30) as response:
            raw = response.read(MAX_PAYLOAD + 1)
        if len(raw) > MAX_PAYLOAD:
            raise ValueError("Issue page exceeds size limit")
        issues = json.loads(raw)
        if not isinstance(issues, list) or len(issues) > 100:
            raise ValueError("Unexpected GitHub response")
        return issues

    def sync_once(self, pages=1):
        """Poll up to ten pages per peer. Signature verification precedes storage."""
        if type(pages) is not int or not 1 <= pages <= 10:
            raise ValueError("pages must be between 1 and 10")
        result = {"verified_new": 0, "already_recorded": 0,
                  "rejected": 0, "scanned": 0}
        for repo in ("genesis", "eve"):
            for page in range(1, pages + 1):
                issues = self._fetch_issues(repo, page)
                for issue in issues:
                    if not isinstance(issue, dict) or issue.get("pull_request"):
                        continue
                    title = issue.get("title", "")
                    if not isinstance(title, str) or not title.startswith(
                        "[Eve peer proposal]" if repo == "genesis" else "[Genesis peer proposal]"
                    ):
                        continue
                    result["scanned"] += 1
                    body = issue.get("body") or ""
                    if not isinstance(body, str) or len(body.encode()) > 45000:
                        result["rejected"] += 1
                        continue
                    match = CODE_PATTERN.fullmatch(body)
                    if not match:
                        result["rejected"] += 1
                        continue
                    try:
                        envelope = json.loads(match.group(1))
                        proposal = envelope["proposal"]
                        expected_sender = "eve" if repo == "genesis" else "genesis"
                        expected_recipient = repo
                        if proposal["sender"] != expected_sender or proposal["recipient"] != expected_recipient:
                            raise ValueError("Wrong direction")
                        verified = verify_envelope(envelope, self.secrets)
                        with self.store.connect() as db:
                            existing = db.execute(
                                "SELECT id,verification_state FROM messages WHERE sender=? AND proposal_id=?",
                                (verified["sender"],verified["proposal_id"])
                            ).fetchone()
                        self.store.record_verified_envelope(envelope, self.secrets, reviewer="lighthouse-github-sync")
                        if existing and existing["verification_state"] == "verified":
                            result["already_recorded"] += 1
                        else:
                            result["verified_new"] += 1
                    except (ValueError, TypeError, KeyError, json.JSONDecodeError, Exception) as exc:
                        # Bad peer content cannot stop the entire synchronization sweep.
                        # Do not print content, tokens or signing keys.
                        result["rejected"] += 1
                if len(issues) < 100:
                    break
        return result
