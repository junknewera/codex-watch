# Codex Watch

LAN dashboard for monitoring local Codex CLI sessions on an Android phone or mobile browser.

## Run on your computer

Requires Python 3.9+ and Codex CLI with local JSONL sessions.

```bash
python3 codex_watch_server.py
```

The server prints a LAN URL and an access token. On a phone connected to the same Wi-Fi, open that URL and enter the token. It reads `CODEX_HOME/sessions` or `~/.codex/sessions` without changing sessions.

This is a **read-only** dashboard. It infers activity from JSONL events and file modification times; it does not control agents. Keep the service on a trusted local network; plain HTTP is not encrypted. Never forward the port to the internet.

The Android Studio project and full design preview from the initial prototype are available in the original ChatGPT project archive. This repository currently contains the lightweight LAN web version.
