#!/usr/bin/env python3
"""Small stdlib-only client for the PolicyLens API.

    python policylens.py login alice policylens
    python policylens.py policies
    python policylens.py submit "Customer API" "We are deploying a new API that stores customer information."
    python policylens.py evidence 3 path/to/iam-policy.json [--type iam] [--note "prod role"]
    python policylens.py controls 3
    python policylens.py evaluate 3
    python policylens.py show 3
    python policylens.py decide 3 return "Attach the retention config."
    python policylens.py audit 3 [--md]

Base URL: $POLICYLENS_URL (default http://localhost:8010). The token is cached in
~/.policylens_token after `login`.
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("POLICYLENS_URL", "http://localhost:8010").rstrip("/")
TOKEN_FILE = Path.home() / ".policylens_token"


def _request(method, path, data=None, form=None, files=None, raw=False):
    headers = {}
    if TOKEN_FILE.exists():
        headers["Authorization"] = f"Bearer {TOKEN_FILE.read_text().strip()}"
    body = None
    if files is not None:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (form or {}).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, p in files.items():
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\n'
                         f"Content-Type: {ctype}\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
        body = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach PolicyLens at {BASE}: {e.reason}")
    return text if raw else json.loads(text)


def show(review):
    print(f"Review #{review['id']}: {review['title']}  [{review['status']}]  result={review['result']}")
    if review.get("summary"):
        print(review["summary"])
    for f in sorted(review["findings"], key=lambda f: ["FAIL", "NEEDS_HUMAN_REVIEW", "UNKNOWN", "PASS"].index(f["status"])):
        ev = ",".join(f"E{i}" for i in f["evidence_ids"]) or "-"
        print(f"- {f['status']:<18} {f['risk']:<6} {f['citation']:<16} evidence={ev}")
        print(f"    policy: {f['policy_text']}")
        print(f"    reading ({f['source']}): {f['interpretation']}")
        for n in f["notes"]:
            print(f"    guardrail: {n}")
    for d in review.get("decisions", []):
        print(f"decision: {d['action']} by {d['reviewer']}: {d['comment']}")


def main():
    # Windows consoles default to a legacy code page and garble the § in citations.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="PolicyLens API client")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("login"); p.add_argument("username"); p.add_argument("password")
    sub.add_parser("policies")
    p = sub.add_parser("submit"); p.add_argument("title"); p.add_argument("description")
    p = sub.add_parser("evidence"); p.add_argument("review_id", type=int); p.add_argument("file")
    p.add_argument("--type", default=""); p.add_argument("--note", default="")
    for name in ("controls", "evaluate", "show"):
        p = sub.add_parser(name); p.add_argument("review_id", type=int)
    p = sub.add_parser("decide"); p.add_argument("review_id", type=int)
    p.add_argument("action", choices=["approve", "reject", "return"]); p.add_argument("comment")
    p = sub.add_parser("audit"); p.add_argument("review_id", type=int); p.add_argument("--md", action="store_true")
    a = ap.parse_args()

    if a.cmd == "login":
        r = _request("POST", "/token", form={"username": a.username, "password": a.password})
        TOKEN_FILE.write_text(r["access_token"])
        print(f"Signed in as {r['username']} ({r['role']})")
    elif a.cmd == "policies":
        for p in _request("GET", "/policies"):
            print(f"{p['policy_key']:<12} {p['title']}  ({p['sections']} sections, {p['requirements']} requirements)")
    elif a.cmd == "submit":
        r = _request("POST", "/reviews", data={"title": a.title, "description": a.description})
        print(f"Created review #{r['id']}")
    elif a.cmd == "evidence":
        r = _request("POST", "/evidence", form={"review_id": a.review_id, "evidence_type": a.type, "note": a.note},
                     files={"file": Path(a.file)})
        print(f"Attached E{r['id']} {r['filename']} as {r['evidence_type']} (detected: {', '.join(r['detected_types'])})")
    elif a.cmd == "controls":
        for c in _request("GET", f"/controls?review_id={a.review_id}"):
            print(f"{c['citation']:<16} {c['risk']:<6} [{c['policy_title']}] {c['text']}")
            print(f"{'':<23} evidence to prepare: {', '.join(c['evidence_types']) or 'reviewer judgement'}")
    elif a.cmd == "evaluate":
        show(_request("POST", "/evaluate", data={"review_id": a.review_id}))
    elif a.cmd == "show":
        show(_request("GET", f"/reviews/{a.review_id}"))
    elif a.cmd == "decide":
        show(_request("POST", "/approve", data={"review_id": a.review_id, "action": a.action, "comment": a.comment}))
    elif a.cmd == "audit":
        if a.md:
            print(_request("GET", f"/audit/{a.review_id}?format=md", raw=True))
        else:
            print(json.dumps(_request("GET", f"/audit/{a.review_id}"), indent=2))


if __name__ == "__main__":
    main()
