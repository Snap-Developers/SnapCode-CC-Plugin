#!/usr/bin/env python3
"""MCP request headers for the cloud MCP: Authorization, plus the tool profile
that identifies this client to the platform.

Claude Code runs this via the `.mcp.json` `headersHelper` on every (re)connect and
merges its stdout JSON into the request headers. This is what stops Claude Code from
attempting OAuth (which 404s on this endpoint) — the server wants an Authorization
header (we send HTTP Basic).

`.mcp.json` points headersHelper straight at this file via ${CLAUDE_PLUGIN_ROOT}
(Claude Code expands that placeholder in headersHelper on v2.1.195+), so the helper
runs in place from the plugin — it is NOT copied anywhere. The headersHelper command
must avoid POSIX-only shell syntax (e.g. `2>/dev/null`): on Windows it may run under
cmd/PowerShell, which treat `/dev/null` as a path and abort the command, yielding an
empty result and a failed MCP connect. Plain `python ... || python3 ...` works on
cmd.exe, PowerShell, and /bin/sh alike.

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
from urllib.parse import urlsplit


CRED_FILE = os.path.expanduser("~/.claude/snapcode/credentials")


def _same_host(a: str, b: str) -> bool:
    try:
        return urlsplit(a).netloc.lower() == urlsplit(b).netloc.lower()
    except ValueError:
        return False


def _creds():
    """Basic-auth creds: env first (back-compat), then the file bootstrap writes.

    Claude Code >=2.1.238 strips credential-named env vars (SNAPLOGIC_API_PASS)
    from a plugin's headersHelper, so on current Claude Code the env path yields
    no password and we fall through to the file the SessionStart hook wrote.
    """
    user, pw = os.environ.get("SNAPLOGIC_API_USER"), os.environ.get("SNAPLOGIC_API_PASS")
    if user and pw:
        return user, pw
    try:
        with open(CRED_FILE) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None, None
    if not isinstance(d, dict):  # valid JSON that isn't an object would crash d.get
        return None, None
    # The file is machine-global but a session is per-pod: refuse creds another
    # session wrote for a different host rather than sending them there. Fail open
    # when either side is unknown (older Claude Code, or a file without base_url).
    want = os.environ.get("CLAUDE_CODE_MCP_SERVER_URL", "")
    have = d.get("base_url") or ""
    if want and have and not _same_host(want, have):
        return None, None
    return d.get("user"), d.get("pass")


def main() -> int:
    # Identify this client to the platform MCP server. The value must be exactly one
    # of its known profiles: resolve_profile_name() lowercases the header and falls
    # back to the (broader) server default on anything it does not recognise, so no
    # version suffix here. Selecting "snapcode" also scopes the tools we are served
    # to the platform + pygen + common set.
    headers = {"X-MCP-Tool-Profile": "snapcode"}
    user, pw = _creds()
    if user and pw:
        b = base64.b64encode(f"{user}:{pw}".encode()).decode()
        headers["Authorization"] = f"Basic {b}"
    # With no creds we still emit the profile but no Authorization, so Claude Code
    # sends no auth (and still does not attempt OAuth).
    print(json.dumps(headers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
