#!/usr/bin/env python3
"""SnapCode plugin bootstrap — runs on every SessionStart, cross-platform (macOS + Windows).

Idempotent: installs the slpy CLI once into the plugin's persistent data dir and
reuses it across sessions. Re-installs only when the bundled wheel changes (version
bump). A no-op on every subsequent session.

POC scope:
  - slpy source = the wheel bundled in the plugin (vendor/). Later this becomes the
    private index (CodeArtifact via broker, or self-hosted PyPI) — only INDEX changes.
  - auth = none yet (local wheel needs none). Later: a one-time SnapLogic login here.

Design notes (why it's written this way):
  - Invoked via hook EXEC form (command="python", args=[this file]) so NO shell is
    involved — avoids the bash-vs-PowerShell problem on Windows. All logic is Python.
  - slpy installs into ${CLAUDE_PLUGIN_DATA} (persists across sessions + plugin updates,
    auto-removed on uninstall), NOT the cwd.
  - Never hard-fails the session: on any error it prints a hint and exits 0.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent))
PLUGIN_DATA = Path(os.environ.get("CLAUDE_PLUGIN_DATA", PLUGIN_ROOT / ".data"))

VENDOR_DIR = PLUGIN_ROOT / "vendor"
TOOL_DIR = PLUGIN_DATA / "tools"        # where uv installs slpy
BIN_DIR = PLUGIN_DATA / "bin"           # where the slpy executable lands
STAMP = PLUGIN_DATA / "installed_wheel.txt"   # records which wheel is installed

# Fixed install location for the MCP auth helper. It must live at a stable, plugin-
# independent path because headersHelper can't locate files inside the plugin
# (${CLAUDE_PLUGIN_ROOT} isn't expanded there). The .mcp.json headersHelper targets
# ~/.claude/snapcode/mcp_headers.py (cross-platform via `~`).
AUTH_DIR = Path.home() / ".claude" / "snapcode"
HELPER_SRC = PLUGIN_ROOT / "bin" / "mcp_headers.py"
HELPER_DST = AUTH_DIR / "mcp_headers.py"
CREDS_DST = AUTH_DIR / "creds.env"


def log(msg: str) -> None:
    print(f"[snapcode-bootstrap] {msg}", file=sys.stderr)


def find_wheel() -> Optional[Path]:
    wheels = sorted(VENDOR_DIR.glob("slpy-*.whl"))
    return wheels[-1] if wheels else None


def ensure_uv() -> Optional[str]:
    """Return path to uv, installing it if missing. Cross-platform."""
    uv = shutil.which("uv")
    if uv:
        return uv
    log("uv not found on PATH — installing…")
    try:
        if os.name == "nt":  # Windows → PowerShell installer
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "irm https://astral.sh/uv/install.ps1 | iex"],
                check=True,
            )
        else:  # macOS / Linux
            subprocess.run(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                shell=True, check=True,
            )
    except subprocess.CalledProcessError as e:
        log(f"failed to install uv: {e}")
        return None
    # uv installs to a user dir not yet on this process's PATH — probe known locations.
    for cand in (shutil.which("uv"),
                 str(Path.home() / ".local" / "bin" / "uv"),
                 str(Path.home() / ".cargo" / "bin" / "uv"),
                 os.path.expandvars(r"%USERPROFILE%\.local\bin\uv.exe")):
        if cand and Path(cand).exists():
            return cand
    return None


def already_installed(wheel: Path) -> bool:
    return STAMP.exists() and STAMP.read_text().strip() == wheel.name


def install_slpy(uv: str, wheel: Path) -> bool:
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, UV_TOOL_DIR=str(TOOL_DIR), UV_TOOL_BIN_DIR=str(BIN_DIR))
    log(f"installing {wheel.name} → {PLUGIN_DATA}")
    try:
        subprocess.run([uv, "tool", "install", "--force", str(wheel)],
                       env=env, check=True)
    except subprocess.CalledProcessError as e:
        log(f"slpy install failed: {e}")
        return False
    STAMP.write_text(wheel.name)
    return True


def install_auth_helper() -> None:
    """Copy the MCP auth helper to its fixed path and seed creds (POC: from repo .env).

    Idempotent. The headersHelper in .mcp.json calls AUTH_DIR/mcp_headers.py.
    """
    try:
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        if HELPER_SRC.exists():
            shutil.copy2(HELPER_SRC, HELPER_DST)
        # POC: seed creds.env from the repo .env if we can find it and creds.env is absent.
        if not CREDS_DST.exists():
            repo_env = Path(os.environ.get("CLAUDE_PROJECT_DIR", PLUGIN_ROOT.parent)) / ".env"
            if repo_env.exists():
                wanted = ("SNAPLOGIC_API_USER", "SNAPLOGIC_API_PASS", "SNAPLOGIC_SLTOKEN")
                lines = [ln for ln in repo_env.read_text(encoding="utf-8").splitlines()
                         if ln.split("=", 1)[0].strip() in wanted]
                if lines:
                    CREDS_DST.write_text("\n".join(lines) + "\n")
                    log(f"seeded creds → {CREDS_DST}")
        log(f"auth helper ready at {HELPER_DST}")
    except Exception as e:  # never break the session over auth-helper setup
        log(f"auth helper setup skipped: {e}")


def main() -> int:
    install_auth_helper()

    wheel = find_wheel()
    if not wheel:
        # No bundled wheel — this is the normal case for the PUBLIC repo (the private
        # slpy source is never shipped here). In production, slpy installs from the
        # private index instead:
        #   uv tool install slpy --index-url <broker-provided CodeArtifact URL>
        # That path needs the token broker (SnapLogic identity -> download token),
        # which is still being built. Until then, slpy is not auto-installed from here.
        log("no bundled wheel (expected in the public repo); slpy installs from the "
            "private index in production — pending the token broker. Skipping for now.")
        return 0

    if already_installed(wheel):
        log(f"slpy up to date ({wheel.name}) — nothing to do")
        return 0

    uv = ensure_uv()
    if not uv:
        log("uv unavailable; cannot install slpy. Install uv and restart the session.")
        return 0

    if install_slpy(uv, wheel):
        exe = "slpy.exe" if os.name == "nt" else "slpy"
        log("done. slpy installed at: " + str(BIN_DIR / exe))
        log(f"add to PATH for this session: {BIN_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
