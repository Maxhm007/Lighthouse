"""Static read-only dashboard generator; NEVER embeds executable message content."""
import html
from pathlib import Path


def render(store, output):
    snapshot = store.snapshot()
    counts = {item["verification_state"]: item["count"] for item in snapshot["messages_by_state"]}
    def esc(value):
        return html.escape(str(value), quote=True)
    rows = []
    for item in snapshot["messages"]:
        rows.append("<tr>" + "".join("<td>" + esc(item[key]) + "</td>" for key in
                    ("sender","recipient","kind","verification_state","received_at")) + "</tr>")
    exp_rows = []
    for item in snapshot["experiments"]:
        exp_rows.append("<tr>" + "".join("<td>" + esc(item[key]) + "</td>" for key in
                        ("title","source","created_at")) + "</tr>")
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none';">
<title>Lighthouse Observatory</title><style>
body{font-family:system-ui,sans-serif;max-width:1080px;margin:35px auto;padding:0 18px;background:#0b1420;color:#eaf3ff}
h1{font-size:2rem}p{color:#9fb3c9}.metrics{display:flex;gap:14px;flex-wrap:wrap}.metric{background:#16283e;border-radius:12px;padding:18px;min-width:120px}
.metric b{display:block;font-size:1.8rem}table{border-collapse:collapse;width:100%;background:#16283e}th,td{padding:12px;border-bottom:1px solid #354963;text-align:left}
small{color:#adc2d5}section{overflow:auto;margin-top:24px}th{color:#c5d8ef}</style></head><body>
<h1>◈ Lighthouse Observatory</h1><p>Read-only research evidence · Genesis × Eve · no live network access</p>
<div class="metrics"><div class="metric"><b>""" + str(counts.get("verified", 0)) + """</b>Verified</div>
<div class="metric"><b>""" + str(counts.get("unverified", 0)) + """</b>Pending</div>
<div class="metric"><b>""" + str(counts.get("rejected", 0)) + """</b>Rejected</div>
<div class="metric"><b>""" + str(len(snapshot["experiments"])) + """</b>Experiments</div></div>
<section><h2>Peer messages</h2><table><thead><tr><th>Sender</th><th>Recipient</th><th>Kind</th><th>Status</th><th>Received</th></tr></thead>
<tbody>""" + ("".join(rows) or "<tr><td colspan='5'>No messages</td></tr>") + """</tbody></table></section>
<section><h2>Evidence experiments</h2><table><thead><tr><th>Title</th><th>Source</th><th>Recorded</th></tr></thead><tbody>""" + ("".join(exp_rows) or "<tr><td colspan='3'>No experiments</td></tr>") + """</tbody></table></section>
<p><small>Generated locally. Unverified messages are not trusted conclusions.</small></p></body></html>"""
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")
    return str(dest)
