#!/usr/bin/env python3
"""SnapCode plugin bootstrap — runs on every SessionStart, cross-platform (macOS + Windows).

Installs the slpy CLI into the plugin's persistent data dir and keeps it reasonably
fresh, without hitting the network on every session.

slpy source:
  The SLServer installer endpoint (which fronts the token broker) — bootstrap GETs
  {SNAPLOGIC_BASE_URL}/api/1/rest/slserver/snapcode/{SNAPCODE_ORG_ID}/fetch_installer
  with the user's SnapLogic credentials (Basic auth). The endpoint returns a short-lived
  private-index URL ({"index_url": ...}), and bootstrap installs slpy from the real
  sl-pypi. Users need no AWS/GitHub.

Update cadence: slpy publishes very frequently, so we DON'T check every session. We check
at most once per TTL window (default 24h). Between checks, an already-installed slpy is
used as-is — no installer call, no network. Channel: develop (newest) for now.

MCP auth: handled separately — this script also copies the MCP auth helper to a fixed
path (~/.claude/snapcode/). The helper reads the user's SnapLogic credentials from their
ENVIRONMENT; this script never handles credentials or reads a repo .env.

Design notes:
  - Invoked via hook EXEC form (command="python3", args=[this file]) so NO shell is
    involved — this is the documented cross-platform pattern and avoids the
    sh-vs-PowerShell problem (a shell-form "a || b" breaks on Windows PowerShell 5.1,
    which lacks the || operator). If python3 is absent on a Windows host so the hook
    doesn't fire, the slpy launcher (bin/slpy + slpy.cmd) re-runs this bootstrap via
    sys.executable on the first `slpy` call, so setup still completes. All logic here
    is Python.
  - slpy installs into ${CLAUDE_PLUGIN_DATA} (persists across sessions + plugin updates).
  - The broker token is passed to uv via ENV (UV_INDEX_* / UV_DEFAULT_INDEX), never on
    the command line, so it doesn't leak into shell history or process listings.
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
# base_url = the user's pod (same as the MCP endpoint); org_id = the user's SnapLogic org.
# Both come from the user's environment. GET + Basic auth returns {index_url: ...}.
SNAPLOGIC_BASE_URL = os.environ.get("SNAPLOGIC_BASE_URL", "").rstrip("/")
# The installer endpoint's org path segment is FIXED — it's the org where the SnapCode
# installer SLServer endpoint lives, the same for every user (NOT the caller's own org).
# Overridable via env only for testing against a different deployment.
SNAPCODE_ORG_ID = os.environ.get("SNAPCODE_ORG_ID", "5be4a4cded5edc0017b9aa70")
# How often to check the index for a newer slpy (seconds). slpy publishes often, so a
# daily check keeps users current without a broker call every session.
CHECK_TTL = int(os.environ.get("SNAPCODE_CHECK_TTL", str(24 * 3600)))

# Fixed install location for the MCP auth helper (headersHelper can't see the plugin dir).
AUTH_DIR = Path.home() / ".claude" / "snapcode"
HELPER_SRC = PLUGIN_ROOT / "bin" / "mcp_headers.py"
HELPER_DST = AUTH_DIR / "mcp_headers.py"

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
def fetch_index_url() -> Optional[str]:
    """Ask the SLServer installer endpoint for a private-index URL.

    GET {base_url}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer with the user's
    SnapLogic credentials (Basic auth). The endpoint verifies the caller and returns
    {"response_map": [{"index_url": "<token-embedded private index URL>", "expires_in": N}]}.

    Credentials + base_url come from the user's environment; org_id is fixed. Returns the
    index URL, or None if anything required is missing or the call fails.
    """
    user = os.environ.get("SNAPLOGIC_API_USER")
    pw = os.environ.get("SNAPLOGIC_API_PASS")
    if not (user and pw):
        log("SNAPLOGIC_API_USER/PASS not set; cannot fetch installer. See SnapCode setup docs.")
        return None
    if not SNAPLOGIC_BASE_URL:
        log("SNAPLOGIC_BASE_URL not set; cannot fetch installer. See SnapCode setup docs.")
        return None
    import base64
    auth = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    url = f"{SNAPLOGIC_BASE_URL}/api/1/rest/slserver/snapcode/{SNAPCODE_ORG_ID}/fetch_installer"
    req = urllib.request.Request(url, method="GET", headers={"Authorization": auth})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except Exception as e:
        log(f"installer request failed ({url}): {e}")
        return None
    # Response shape: {"response_map": [{"index_url": ...}]} (list). Fall back to a flat
    # {"index_url": ...} just in case the endpoint shape changes.
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


# ── auth helper ─────────────────────────────────────────────────────────────--
def install_auth_helper() -> None:
    """Place the MCP auth helper at its fixed path (it reads creds from the env at runtime)."""
    try:
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        if HELPER_SRC.exists():
            shutil.copy2(HELPER_SRC, HELPER_DST)
            log(f"auth helper ready at {HELPER_DST}")
        else:
            log(f"auth helper source missing: {HELPER_SRC}")
    except Exception as e:
        log(f"auth helper setup skipped: {e}")


# ── main ───────────────────────────────────────────────────────────────────--
def main() -> int:
    install_auth_helper()  # independent of slpy — MCP must work even if slpy isn't installed

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
        "Check SNAPLOGIC_BASE_URL, SNAPCODE_ORG_ID, and your SnapLogic credentials "
        "(see setup docs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
