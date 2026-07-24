#!/usr/bin/env python3
"""SnapCode plugin bootstrap — runs on every SessionStart, cross-platform (macOS + Windows).

Installs the slpy CLI into the plugin's persistent data dir and keeps it reasonably
fresh, without hitting the network on every session.

slpy source:
  The SLServer installer endpoint (which fronts the token broker) — bootstrap GETs
  {SNAPLOGIC_BASE_URL}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer
  with the user's SnapLogic credentials (Basic auth). The endpoint returns a short-lived
  private-index URL ({"response_map": [{"index_url": ...}]}), and bootstrap installs slpy
  from the real sl-pypi. Users need no AWS/GitHub.
  org_id is resolved from SNAPLOGIC_ORG_ID (direct hex ID) or SNAPLOGIC_ORG_NAME (bootstrap
  looks it up via /api/1/rest/public/users/{email}).

Update cadence: slpy publishes very frequently, so we DON'T check every session. We check
at most once per TTL window (default 24h). Between checks, an already-installed slpy is
used as-is — no installer call, no network. Channel: develop (newest) for now.

MCP auth: handled separately — this script also copies the MCP auth helper to a fixed
path (~/.claude/snapcode/). The helper reads the user's SnapLogic credentials from their
ENVIRONMENT; this script never handles credentials or reads a repo .env.

Design notes:
  - Invoked from the SessionStart hook as `python3 "${CLAUDE_PLUGIN_ROOT}/bin/bootstrap.py"`.
    The hook needs a `matcher` (e.g. "startup|resume|clear") or it registers but never fires.
    All the real logic is Python (not shell), keeping it cross-platform. If python3 is absent
    on a Windows host so the hook doesn't fire, the slpy launcher (bin/slpy + slpy.cmd) re-runs
    this bootstrap via sys.executable on the first `slpy` call, so setup still completes.
  - slpy installs into ${CLAUDE_PLUGIN_DATA} (persists across sessions + plugin updates).
  - The broker token is passed to uv via ENV (UV_DEFAULT_INDEX), never on the command
    line, so it doesn't leak into shell history or process listings.
  - Never hard-fails the session: on any error it logs a hint and exits 0.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
PLUGIN_DATA = Path(os.environ.get("CLAUDE_PLUGIN_DATA", PLUGIN_ROOT / ".data"))

TOOL_DIR = PLUGIN_DATA / "tools"        # where uv installs slpy
BIN_DIR = PLUGIN_DATA / "bin"           # where the slpy executable lands
LAST_CHECK = PLUGIN_DATA / "last_check"  # timestamp of last broker/index check

# The installer endpoint lives on the SnapLogic SLServer:
#   {base_url}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer
# base_url = the user's pod (same host as the MCP endpoint), from the user's environment.
SNAPLOGIC_BASE_URL = os.environ.get("SNAPLOGIC_BASE_URL", "").rstrip("/")
# Org ID for the fetch_installer URL path. Two ways to provide it (ID takes priority):
#   SNAPLOGIC_ORG_ID  — the 24-char hex org ID directly (e.g. from Manager > Settings)
#   SNAPLOGIC_ORG_NAME — the org name (e.g. "mycompany"); bootstrap resolves it to an ID
#                       via GET /api/1/rest/public/users/{email} on first run.
# If neither is set, bootstrap logs a hint and skips slpy installation.
SNAPLOGIC_ORG_ID = os.environ.get("SNAPLOGIC_ORG_ID", "")
SNAPLOGIC_ORG_NAME = os.environ.get("SNAPLOGIC_ORG_NAME", "")
# How often to check the index for a newer slpy (seconds). slpy publishes often, so a
# daily check keeps users current without a broker call every session.
CHECK_TTL = int(os.environ.get("SNAPCODE_CHECK_TTL", str(24 * 3600)))

# Note: the MCP auth helper (bin/mcp_headers.py) is referenced directly from .mcp.json
# via ${CLAUDE_PLUGIN_ROOT}, so bootstrap no longer copies it anywhere — that removes the
# first-session race where the MCP tried to connect before the helper was in place.

SLPY_EXE = BIN_DIR / ("slpy.exe" if os.name == "nt" else "slpy")


def log(msg: str) -> None:
    print(f"[snapcode-bootstrap] {msg}", file=sys.stderr)


# ── uv ────────────────────────────────────────────────────────────────────────
def ensure_uv() -> Optional[str]:
    """Return path to uv, installing it if missing. Cross-platform."""
    uv = shutil.which("uv")
    if uv:
        return uv
    log("uv not found on PATH — installing…")
    try:
        if os.name == "nt":
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "irm https://astral.sh/uv/install.ps1 | iex"], check=True)
        else:
            subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh",
                           shell=True, check=True)
    except subprocess.CalledProcessError as e:
        log(f"failed to install uv: {e}")
        return None
    for cand in (shutil.which("uv"),
                 str(Path.home() / ".local" / "bin" / "uv"),
                 str(Path.home() / ".cargo" / "bin" / "uv"),
                 os.path.expandvars(r"%USERPROFILE%\.local\bin\uv.exe")):
        if cand and Path(cand).exists():
            return cand
    return None


# ── timing ────────────────────────────────────────────────────────────────────
def check_due() -> bool:
    """True if we haven't checked the index within the TTL window."""
    if not SLPY_EXE.exists():
        return True  # not installed yet — must install
    if not LAST_CHECK.exists():
        return True
    try:
        last = float(LAST_CHECK.read_text().strip())
    except Exception:
        return True
    return (time.time() - last) >= CHECK_TTL


def mark_checked() -> None:
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    LAST_CHECK.write_text(str(time.time()))


# ── installer endpoint (SLServer) ─────────────────────────────────────────────
# Identify the SnapCode plugin as a real client. Some pods (e.g. canary) sit behind
# Cloudflare bot protection that rejects the default Python-urllib User-Agent with a
# 1010 error; a proper UA identifies our legitimate client (like gh/aws CLIs do).
USER_AGENT = "snapcode-plugin-bootstrap/0.1 (+https://github.com/Snap-Developers/SnapCode-CC-Plugin)"


def _request_headers(user: str, pw: str) -> dict:
    import base64
    return {
        "Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode(),
        "User-Agent": USER_AGENT,
    }


def resolve_org_id(user: str, pw: str) -> Optional[str]:
    """Resolve org ID from SNAPLOGIC_ORG_ID (direct) or SNAPLOGIC_ORG_NAME (lookup).

    Priority:
      1. SNAPLOGIC_ORG_ID — used as-is (no network call needed)
      2. SNAPLOGIC_ORG_NAME — resolved via GET /api/1/rest/public/users/{email},
         which returns the user's org list with IDs. No admin required.

    Returns the org ID string, or None if it can't be determined.
    """
    import urllib.parse

    if SNAPLOGIC_ORG_ID:
        return SNAPLOGIC_ORG_ID

    if not SNAPLOGIC_ORG_NAME:
        log("Neither SNAPLOGIC_ORG_ID nor SNAPLOGIC_ORG_NAME is set. "
            "Set one of them to install slpy. See SnapCode setup docs.")
        return None

    # Look up org ID from org name via the platform user API.
    url = f"{SNAPLOGIC_BASE_URL}/api/1/rest/public/users/{urllib.parse.quote(user, safe='')}"
    req = urllib.request.Request(url, headers=_request_headers(user, pw))
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            orgs = json.load(r).get("organizations", [])
    except Exception as e:
        log(f"org lookup failed ({url}): {e} — set SNAPLOGIC_ORG_ID directly to skip lookup.")
        return None

    matches = [o for o in orgs if o.get("name", "").lower() == SNAPLOGIC_ORG_NAME.lower()]
    if not matches:
        names = [o.get("name") for o in orgs]
        log(f"org '{SNAPLOGIC_ORG_NAME}' not found. Available: {names}. "
            "Check SNAPLOGIC_ORG_NAME or use SNAPLOGIC_ORG_ID directly.")
        return None

    org_id = matches[0]["id"]
    log(f"resolved org '{SNAPLOGIC_ORG_NAME}' → {org_id}")
    return org_id


def fetch_index_url() -> Optional[str]:
    """Ask the SLServer installer endpoint for a private-index URL.

    GET {base_url}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer with the user's
    SnapLogic credentials (Basic auth). The endpoint verifies the caller and returns
    {"response_map": [{"index_url": "<token-embedded private index URL>", "expires_in": N}]}.

    Org ID is resolved from SNAPLOGIC_ORG_ID (direct) or SNAPLOGIC_ORG_NAME (lookup).
    Returns the index URL, or None if anything required is missing or the call fails.
    """
    user = os.environ.get("SNAPLOGIC_API_USER")
    pw = os.environ.get("SNAPLOGIC_API_PASS")
    if not (user and pw):
        log("SNAPLOGIC_API_USER/PASS not set; cannot fetch installer. See SnapCode setup docs.")
        return None
    if not SNAPLOGIC_BASE_URL:
        log("SNAPLOGIC_BASE_URL not set; cannot fetch installer. See SnapCode setup docs.")
        return None

    org_id = resolve_org_id(user, pw)
    if not org_id:
        return None

    url = f"{SNAPLOGIC_BASE_URL}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer"
    req = urllib.request.Request(url, method="GET", headers=_request_headers(user, pw))
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except Exception as e:
        log(f"installer request failed ({url}): {e}")
        return None
    # Response shape: {"response_map": [{"index_url": ...}]} (list). Fall back to flat shape.
    rmap = body.get("response_map")
    if isinstance(rmap, list) and rmap:
        return rmap[0].get("index_url")
    if isinstance(rmap, dict):
        return rmap.get("index_url")
    return body.get("index_url")


def install_slpy_from_index(uv: str, index_url: str) -> bool:
    """Install/update slpy from the private index. Token is passed via ENV, not argv."""
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    # Pass the token-bearing index URL through the environment so it never appears on
    # the command line (shell history / ps). uv reads UV_DEFAULT_INDEX.
    env = dict(os.environ,
               UV_TOOL_DIR=str(TOOL_DIR), UV_TOOL_BIN_DIR=str(BIN_DIR),
               UV_DEFAULT_INDEX=index_url)
    log("installing/updating slpy from the private index…")
    try:
        subprocess.run([uv, "tool", "install", "--force", "slpy"], env=env, check=True)
    except subprocess.CalledProcessError as e:
        log(f"slpy install failed: {e}")
        return False
    return True


# ── main ───────────────────────────────────────────────────────────────────--
def main() -> int:
    # MCP auth no longer needs setup here — .mcp.json points headersHelper straight at
    # ${CLAUDE_PLUGIN_ROOT}/bin/mcp_headers.py, which exists at install time.
    if not check_due():
        log(f"slpy present and checked within {CHECK_TTL // 3600}h — skipping")
        return 0

    uv = ensure_uv()
    if not uv:
        log("uv unavailable; cannot install slpy. Install uv and restart the session.")
        return 0

    # Install/update slpy from the private index via the SLServer installer endpoint.
    index_url = fetch_index_url()
    if index_url and install_slpy_from_index(uv, index_url):
        mark_checked()
        log(f"done. slpy ready at {SLPY_EXE}")
        return 0

    log("slpy not installed: installer endpoint unreachable or credentials missing. "
        "Check SNAPLOGIC_BASE_URL and your SnapLogic credentials (see setup docs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
