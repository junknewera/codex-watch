#!/usr/bin/env python3
"""Read-only LAN monitor for local Codex CLI JSONL sessions."""
import argparse
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
TOKEN_PATH = Path.home() / ".codex-watch" / "token"

def get_token():
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    token = secrets.token_urlsafe(32)
    TOKEN_PATH.write_text(token)
    try: TOKEN_PATH.chmod(0o600)
    except OSError: pass
    return token

def sessions():
    root = CODEX_HOME / "sessions"
    if not root.exists():
        return []
    paths = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]
    output = []
    for path in paths:
        try:
            mtime = path.stat().st_mtime
            if time.time() - mtime > 86400: continue
            events = []
            with path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 180000))
                if size > 180000: f.readline()
                for line in f:
                    try: events.append(json.loads(line))
                    except (ValueError, UnicodeDecodeError): pass
            if not events: continue
            meta = next((e.get("payload", {}) for e in events if e.get("type") == "session_meta"), {})
            project = meta.get("cwd") or str(path.parent)
            recent = events[-50:]
            state = "idle"
            for e in reversed(recent):
                p = e.get("payload", {})
                kind = p.get("type") or e.get("type")
                if kind in ("task_complete", "turn_complete"): state = "done"; break
                if kind in ("task_started", "turn_started"): state = "running"; break
                if kind in ("turn_aborted",): state = "interrupted"; break
            if state == "running" and time.time() - mtime > 120: state = "idle"
            timeline = []
            for e in recent[-12:]:
                p = e.get("payload", {})
                kind = str(p.get("type") or e.get("type") or "event")
                text = p.get("message") or p.get("text") or ""
                if not isinstance(text, str): text = ""
                timeline.append({"time": e.get("timestamp", ""), "type": kind, "text": text[:250]})
            output.append({"id": meta.get("id") or path.stem, "project": project,
                           "status": state, "updated": mtime, "events": timeline})
        except (OSError, ValueError):
            continue
    return output[:25]

class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, kind="application/json"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send(200, (ROOT / "web" / "index.html").read_text(encoding="utf-8"), "text/html")
        elif path == "/api/status":
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not secrets.compare_digest(supplied, TOKEN):
                self.send(401, json.dumps({"error": "Unauthorized"}))
            else:
                self.send(200, json.dumps({"sessions": sessions(), "server_time": time.time()}))
        else:
            self.send(404, json.dumps({"error": "Not found"}))

    def do_POST(self):
        self.send(405, json.dumps({"error": "Read only"}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--codex-home")
    args = parser.parse_args()
    if args.codex_home: CODEX_HOME = Path(args.codex_home)
    TOKEN = get_token()
    print("Codex Watch: http://<YOUR-PC-LAN-IP>:%d" % args.port)
    print("Access token:", TOKEN)
    print("Do not expose this HTTP service to the internet.")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
else:
    TOKEN = get_token()
