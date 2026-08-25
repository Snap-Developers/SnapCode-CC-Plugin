#!/usr/bin/env python3
"""MCP auth helper — emits the Authorization header for the cloud MCP.

Claude Code runs this via the `.mcp.json` `headersHelper` on every (re)connect and
merges its stdout JSON into the request headers. Whatever this helper prints decides
which auth scheme the MCP connection uses:

  * print an `Authorization` header  -> Claude Code uses it and does NOT start OAuth.
  * print `{}` (no header)           -> the request goes out unauthenticated, the server
                                        answers 401 with an RFC 9728 `WWW-Authenticate`
                                        challenge, and Claude Code follows it into its
                                        own OAuth browser sign-in.

Two auth modes, selected by SNAPLOGIC_AUTH_MODE:

  * (unset) / `basic` — DEFAULT. HTTP Basic from SNAPLOGIC_API_USER + SNAPLOGIC_API_PASS.
    Unchanged behaviour: creds set -> Basic header; creds absent -> `{}`.
  * `oauth` — opt in to the platform's own OAuth authorization server. This helper emits
    `{}` even when SNAPLOGIC_API_USER/PASS are set, so Claude Code signs in through the
    browser instead. That matters because the slpy installer (`bootstrap.py`) still needs
    those Basic creds in the environment — without this switch there is no way to keep the
    installer working while moving the MCP surface onto SSO.

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

SLToken is intentionally NOT supported here: it must be copied manually from the UI and
expires, which is poor UX. Basic remains the default because it needs no browser and no
setup beyond two env vars; `SNAPLOGIC_AUTH_MODE=oauth` is the opt-in path to short-lived,
browser-issued tokens on pods whose MCP endpoint fronts the platform's authorization
server. See the SnapCode setup docs for how to test that mode.
"""

import base64
import json
import os
import sys


def main() -> int:
    env = os.environ
    mode = env.get("SNAPLOGIC_AUTH_MODE", "").strip().lower()
    user, pw = env.get("SNAPLOGIC_API_USER"), env.get("SNAPLOGIC_API_PASS")
    if mode == "oauth":
        # Opt-in: emit no header so Claude Code follows the server's 401 challenge
        # into OAuth, even though Basic creds may be set for the slpy installer.
        print("{}")
    elif user and pw:
        b = base64.b64encode(f"{user}:{pw}".encode()).decode()
        print(json.dumps({"Authorization": f"Basic {b}"}))
    else:
        # No creds set — emit empty object, no auth header. The server's 401 challenge
        # will make Claude Code offer OAuth; set SNAPLOGIC_AUTH_MODE=oauth to choose
        # that deliberately rather than by omission.
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
