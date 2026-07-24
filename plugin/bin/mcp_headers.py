#!/usr/bin/env python3
"""MCP auth helper — emits the Authorization header for the cloud MCP.

Claude Code runs this via the `.mcp.json` `headersHelper` on every (re)connect and
merges its stdout JSON into the request headers. This is what stops Claude Code from
attempting OAuth (which 404s on this endpoint) — the server wants an Authorization
header (we send HTTP Basic).

IMPORTANT (why this file is INSTALLED to a fixed path, not run from the plugin):
`headersHelper` does NOT expand ${CLAUDE_PLUGIN_ROOT} and does NOT receive
CLAUDE_PLUGIN_ROOT/DATA in its env (only CLAUDE_CODE_MCP_SERVER_NAME/_URL). So a
plugin can't point headersHelper at a file inside itself. bootstrap.py copies this
helper to ~/.claude/snapcode/ and the .mcp.json headersHelper targets that fixed
path (cross-platform via `~`).

Credentials come from the user's ENVIRONMENT — SNAPLOGIC_API_USER + SNAPLOGIC_API_PASS.
Users set these in their own shell per the SnapCode setup docs, and Claude Code passes
the environment through to this helper (verified). No repo, no GitHub, no AWS.

We use username/password (HTTP Basic) only. SLToken is intentionally NOT supported here:
it must be copied manually from the UI and expires, which is poor UX. A future
`snapcode login` flow (browser/OAuth) is the planned path to short-lived, auto-refreshed
tokens — until then, Basic is the simplest option that works.
"""

import base64
import json
import os
import sys


def main() -> int:
    env = os.environ
    user, pw = env.get("SNAPLOGIC_API_USER"), env.get("SNAPLOGIC_API_PASS")
    if user and pw:
        b = base64.b64encode(f"{user}:{pw}".encode()).decode()
        print(json.dumps({"Authorization": f"Basic {b}"}))
    else:
        # No creds set — emit empty object so Claude Code sends no auth (still no OAuth).
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
