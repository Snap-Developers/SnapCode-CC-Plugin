#!/usr/bin/env python3
"""MCP auth helper — emits the Authorization header for the cloud MCP.

Claude Code runs this via the `.mcp.json` `headersHelper` on every (re)connect and
merges its stdout JSON into the request headers. This is what stops Claude Code from
attempting OAuth (which 404s on this endpoint) — the server wants an Authorization
header (we send HTTP Basic).

Path note: .mcp.json invokes this as `python bin/mcp_headers.py` — a RELATIVE path.
Claude Code runs headersHelper with the working directory set to the plugin root, so
the relative path resolves on every platform. We deliberately do NOT use
${CLAUDE_PLUGIN_ROOT} here: that placeholder is expanded on macOS but NOT on Windows
(it comes through empty), which broke the auth header and the MCP connection on Windows.
`python || python3` covers both platforms (Windows real Python is `python`; many
macOS/Linux setups only have `python3`).

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
