#!/usr/bin/env python3
"""MCP request headers for the SnapLogic MCP server: Authorization, plus the tool profile
that identifies this client to the platform.

Claude Code runs this via the `.mcp.json` `headersHelper` on every connection and again
after a 401, and merges its stdout JSON into the request headers. `.mcp.json` points at
this file via ${CLAUDE_PLUGIN_ROOT}, so it runs in place from the plugin. The
headersHelper command must avoid POSIX-only shell syntax (e.g. `2>/dev/null`): on
Windows it may run under cmd/PowerShell, which treat `/dev/null` as a path and abort
the command. Plain `python ... || python3 ...` works on cmd.exe, PowerShell and /bin/sh.

Where the credential comes from, in the order the snaplogic CLI uses:

1. A username and password. Claude Code does not pass credential-named variables
   (SNAPLOGIC_API_PASS) to a plugin's headersHelper, nor anything that says which
   session it serves, so the SessionStart hook records in CRED_FILE, per deployment,
   whether its session has a password, and the password when it does. This helper
   uses it only for the deployment it connects to, and only when the entry says
   password: a session without one replaces a password an earlier session left.
   The single-entry file earlier versions write is read only until the first session
   start creates this one.
2. The token from a browser sign-in (`snaplogic auth login`), read with
   `snaplogic auth token`, which renews it first when it is close to expiring. The MCP
   endpoint takes it as a Bearer token. This is how a user with SSO, who has no
   password to give, reaches the MCP server. When there is no token, or it cannot be
   read, nothing else is tried: a lapsed sign-in never turns into a password retry.
3. Neither: a Bearer value that can never be valid. A rejected Bearer shows as the
   helper's credential being refused, and the session start's checklist says how to
   sign in. It carries no username, so it counts toward no account's lockout.

If this helper fails, Claude Code falls back to the MCP server's own OAuth sign-in.
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


CRED_FILE = os.path.expanduser("~/.claude/snapcode/mcp-credentials.json")
# The single-entry file earlier versions write. See _legacy_creds().
LEGACY_CRED_FILE = os.path.expanduser("~/.claude/snapcode/credentials")
# `snaplogic auth token` renews within a 5 s budget; Claude Code gives this helper 10 s.
CLI_TIMEOUT = 8
NOT_SIGNED_IN = "Bearer snapcode-not-signed-in"


def _deployment(url: str) -> str:
    """The deployment a URL names, the way the snaplogic CLI keys its logins:
    lowercase host, and cdn.<host> is <host> behind Cloudflare.

    Must give the same key as bootstrap.py's _deployment(), which keys the entries
    this looks up, so it is written the same way. urlsplit() would not do: it finds
    no host at all in an address without a scheme."""
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    return host[len("cdn."):] if host.startswith("cdn.") else host


def _origin(url: str) -> str:
    u = urlsplit(url)
    return f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else ""


def _plugin_data_dir() -> Path:
    """The same resolution as bootstrap.py's _plugin_data_dir(). Claude Code does not
    set CLAUDE_PLUGIN_DATA for a headersHelper, so the stable path is what applies."""
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env:
        return Path(env)
    stable = Path.home() / ".claude" / "plugins" / "data" / "snapcode-snapcode"
    if stable.parent.exists():
        return stable
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parent.parent)
    return Path(root) / ".data"


def _token(base_url: str):
    """A signed-in user's token, or None. The CLI itself, not its launcher: the
    launcher runs bootstrap when the CLI is missing, which can outlast the 10 s this
    helper has."""
    if not base_url:
        return None
    data = _plugin_data_dir()
    for name in ("snaplogic", "snaplogic.exe"):
        cli = data / "bin" / name
        if cli.exists():
            break
    else:
        return None
    env = dict(os.environ)
    # The CLI reads the address from SNAPLOGIC_BASE_URL only. Set it to the address this
    # MCP server is at, which is what the token has to be for.
    env["SNAPLOGIC_BASE_URL"] = base_url
    # Getting here means there is no whole password to use, but Claude Code hands a
    # headersHelper SNAPLOGIC_API_USER while it strips SNAPLOGIC_API_PASS, and half
    # of a password stops `auth token`. The token is what is wanted here.
    env.pop("SNAPLOGIC_API_USER", None)
    env.pop("SNAPLOGIC_API_PASS", None)
    try:
        env.setdefault("SNAPLOGIC_CLIENT", (data / "client_token").read_text().strip() or "snapcode")
    except FileNotFoundError:  # MCP connects alongside the first session start, which writes it
        env.setdefault("SNAPLOGIC_CLIENT", "snapcode")
    try:
        r = subprocess.run([str(cli), "auth", "token"],
                           capture_output=True, text=True, timeout=CLI_TIMEOUT, env=env)
    # A CLI that hangs, or one built for another machine ("Exec format error").
    except (subprocess.TimeoutExpired, OSError):
        return None
    token = r.stdout.strip()
    return token if r.returncode == 0 and token else None


def _creds(base_url: str):
    """Basic-auth creds: env first (a user-scope server still gets it), then this
    deployment's entry in the file bootstrap writes, when it is a password."""
    user, pw = os.environ.get("SNAPLOGIC_API_USER"), os.environ.get("SNAPLOGIC_API_PASS")
    if user and pw:
        return user, pw
    if not base_url:
        return None, None
    try:
        with open(CRED_FILE) as f:
            d = json.load(f)
    except FileNotFoundError:
        return _legacy_creds(base_url)
    entries = d.get("deployments") if isinstance(d, dict) else None
    entry = entries.get(_deployment(base_url)) if isinstance(entries, dict) else None
    if not (isinstance(entry, dict) and entry.get("method") == "password"):
        return None, None
    return entry.get("user"), entry.get("pass")


def _legacy_creds(base_url: str):
    """The password an earlier version wrote to LEGACY_CRED_FILE, for its own deployment.

    Read only while CRED_FILE does not exist yet. On the first session after the
    update MCP connects alongside the hook that creates it, and without this every
    password user's first session would start with MCP rejected. Once CRED_FILE
    exists this file is never read, so a password it still holds is not sent.
    """
    try:
        with open(LEGACY_CRED_FILE) as f:
            d = json.load(f)
    except FileNotFoundError:
        return None, None
    if not (isinstance(d, dict) and d.get("user") and d.get("pass")):
        return None, None
    if _deployment(d.get("base_url") or "") != _deployment(base_url):
        return None, None
    return d.get("user"), d.get("pass")


def headers() -> dict:
    # Identify this client to the platform MCP server. The value must be exactly one
    # of its known profiles: resolve_profile_name() lowercases the header and falls
    # back to the (broader) server default on anything it does not recognise, so no
    # version suffix here. Selecting "snapcode" also scopes the tools we are served
    # to the platform + pygen + common set.
    h = {"X-MCP-Tool-Profile": "snapcode"}
    base_url = (_origin(os.environ.get("CLAUDE_CODE_MCP_SERVER_URL", ""))
                or os.environ.get("SNAPLOGIC_BASE_URL", "").rstrip("/"))
    user, pw = _creds(base_url)
    if user and pw:
        h["Authorization"] = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
        return h
    token = _token(base_url)
    h["Authorization"] = f"Bearer {token}" if token else NOT_SIGNED_IN
    return h


def main() -> int:
    print(json.dumps(headers()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
