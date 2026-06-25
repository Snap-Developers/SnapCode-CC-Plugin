#!/usr/bin/env python3
"""MCP auth helper — emits the Authorization header for the cloud MCP.

Claude Code runs this via the `.mcp.json` `headersHelper` on every (re)connect and
merges its stdout JSON into the request headers. This is what stops Claude Code from
attempting OAuth (which 404s on this endpoint) — the server wants Basic / SLToken.

IMPORTANT (why this file is INSTALLED to a fixed path, not run from the plugin):
`headersHelper` does NOT expand ${CLAUDE_PLUGIN_ROOT} and does NOT receive
CLAUDE_PLUGIN_ROOT/DATA in its env (only CLAUDE_CODE_MCP_SERVER_NAME/_URL). So a
plugin can't point headersHelper at a file inside itself. bootstrap.py copies this
helper to ~/.claude/snapcode/ and the .mcp.json headersHelper targets that fixed
path (cross-platform via `~`).

Creds source: creds.env next to this file.
  - POC: bootstrap seeds it from the repo .env.
  - Product: the login flow writes a cached SLToken here and refreshes it; this
    helper just reads whatever is current on each connect.
"""

import base64
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CREDS = HERE / "creds.env"


def load(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip()
    return out


def main() -> int:
    env = {**load(CREDS), **os.environ}
    tok = env.get("SNAPLOGIC_SLTOKEN")
    user, pw = env.get("SNAPLOGIC_API_USER"), env.get("SNAPLOGIC_API_PASS")
    if tok:
        print(json.dumps({"Authorization": f"SLToken {tok}"}))
    elif user and pw:
        b = base64.b64encode(f"{user}:{pw}".encode()).decode()
        print(json.dumps({"Authorization": f"Basic {b}"}))
    else:
        # No creds yet — emit empty object so Claude Code sends no auth (still no OAuth).
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
