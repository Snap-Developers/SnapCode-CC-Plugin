#!/usr/bin/env python3
"""SnapCode plugin bootstrap — runs on every SessionStart, cross-platform (macOS + Windows).

Gets the machine ready: the `snaplogic` CLI first, then the slpy toolchain through it.

In order:
  1. Mirror Basic credentials from the environment into a file the MCP headers helper
     can read (see write_credentials). Unchanged by everything below: that moved the
     *slpy* credential out of the plugin, while MCP still authenticates with Basic for
     everyone who has not moved to SSO.
  2. Download the public `snaplogic` CLI if it is not here yet. No credentials are
     involved, which is the whole reason the plugin can fetch a binary rather than ask
     the user to install one.
  3. Ask the CLI whether anyone is signed in, and say how to if not. Signing in opens a
     browser, which this hook cannot do, so it can only ask.
  4. Run `snaplogic slpy install`, which reaches the installer endpoint, resolves the
     org and drives uv, using the CLI's own credentials.

Steps 3 and 4 used to happen here, holding the user's password: bootstrap resolved the
org itself, called fetch_installer over HTTP Basic, and ran uv. Moving them into the CLI
is what lets an SSO user, who has no password at all, set SnapCode up.

Update cadence: slpy publishes very frequently, so we DON'T check every session. We check
at most once per TTL window (default 24h). Between checks, an already-installed slpy is
used as-is — no installer call, no network. Channel: develop (newest) for now.

MCP auth: .mcp.json points headersHelper straight at ${CLAUDE_PLUGIN_ROOT}/bin/mcp_headers.py,
which runs in place from the plugin. Claude Code >=2.1.238 no longer passes credential-named
env vars (SNAPLOGIC_API_PASS) to a plugin's headersHelper, so on SessionStart we mirror the
credentials from the environment (still available to this hook) into a file the helper reads;
see write_credentials(). We never read a repo .env.

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

import contextlib
import functools
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

# ── what the user sees ────────────────────────────────────────────────────────
AUTO_UPDATE_HOW = "/plugin → Marketplaces → snapcode → Enable auto-update"
AUTO_UPDATE_WHEN = ("Within 10 minutes of your next message, Claude Code installs it and "
                    "asks you to run /reload-plugins.")
CHECK_MCP_CONNECTED = "run /mcp to check it is connected"

UPDATE_AVAILABLE = (
    "Update: SnapCode {latest} is available (you have {current}). Two ways to update:\n"
    "   • Turn on auto-update: " + AUTO_UPDATE_HOW + ".\n"
    "     " + AUTO_UPDATE_WHEN + " Later versions then install the same way.\n"
    "   • Or update manually, then run /reload-plugins:\n"
    "       claude plugin marketplace update snapcode\n"
    "       claude plugin update snapcode@snapcode"
)
UPDATE_AVAILABLE_AUTO = "Update: SnapCode {latest} is available (you have {current}). " + AUTO_UPDATE_WHEN
AUTO_UPDATE_TIP = "Tip: Turn on auto-update so SnapCode stays current: " + AUTO_UPDATE_HOW + "."

WELCOME = (
    "Welcome to SnapCode. This plugin gives you:\n"
    "  • The `snaplogic` CLI — ready in this session\n"
    "  • The `slpy` CLI — installed and kept up to date for you\n"
    "  • The SnapLogic MCP server — snap discovery and platform tools\n"
    "  • Skills:\n"
    "{skills}"
)
SKILL_SUMMARIES = {
    "snaplogic-slpy-gen": "generate pipelines and expression libraries",
    "snaplogic-deploy": "deploy, validate and fix pipelines on the platform",
    "agent-pipelines": "build agent pipelines (AgentCreator)",
    "mcp-server-pipelines": "build an MCP server pipeline and the tools it exposes",
}

CHECKLIST_TITLE = "SnapCode {version} checklist"
CHECK_CLI = "snaplogic CLI — {version}"
CHECK_CLI_MISSING = "snaplogic CLI — not available"
CHECK_SIGN_IN_NO_ADDRESS = "Sign-in — no SnapLogic address: SNAPLOGIC_BASE_URL is not set"
CHECK_SIGN_IN_CLI_SAYS = "Sign-in — {message}"
CHECK_SIGN_IN_NO_ANSWER = "Sign-in — `snaplogic auth status` did not answer"
CHECK_SIGN_IN_PASSWORD = "Sign-in — password from SNAPLOGIC_API_USER ({user})"
CHECK_SIGN_IN_BROWSER = "Sign-in — `snaplogic auth status`: signed in as {user} (browser sign-in)"
CHECK_SIGN_IN_BROWSER_NO_USER = "Sign-in — `snaplogic auth status`: signed in (browser sign-in)"
CHECK_SIGN_IN_OUT = "Sign-in — `snaplogic auth status`: not signed in to {host}"
CHECK_SLPY = "slpy — {version}"
CHECK_SLPY_INSTALLED = "slpy — installed"
CHECK_SLPY_CLI_SAYS = "slpy — {message}"
CHECK_SLPY_MISSING = "slpy — not installed"
CHECK_MCP_PASSWORD = "SnapLogic MCP — configured for {host} · " + CHECK_MCP_CONNECTED
CHECK_MCP_SAVED_PASSWORD = ("SnapLogic MCP — configured for {host}, with the password a newer "
                            "session saved · " + CHECK_MCP_CONNECTED)
CHECK_MCP_BROWSER = ("SnapLogic MCP — configured for {host}, with your browser sign-in · "
                     + CHECK_MCP_CONNECTED)
CHECK_MCP_NOT_SIGNED_IN = ("SnapLogic MCP — not signed in: sign in (below), or set "
                           "SNAPLOGIC_API_USER / SNAPLOGIC_API_PASS")
CHECK_MCP_NO_ADDRESS = "SnapLogic MCP — SNAPLOGIC_BASE_URL is not set"
CHECK_SKILLS = "Skills — {count} ready: {names}"
CHECK_SKILLS_NONE = "Skills — none found"

NO_ADDRESS_NOTE = ("Warning: no SnapLogic address is configured{cost} Set "
                   "SNAPLOGIC_BASE_URL to your control plane URL, for example "
                   "https://elastic.snaplogic.com, and restart this session.")
NOT_SIGNED_IN_NOTE = "Warning: you are not signed in to SnapLogic{cost} {steps}"
COST_SLPY_INSTALLED = (". slpy is installed but will not be kept up to date, and `snaplogic` "
                       "commands that reach the platform will fail.")
COST_SLPY_MISSING = ", so the slpy CLI was not installed."
COST_NO_CLI = ", so the `snaplogic` and slpy CLIs were not set up."
SIGN_IN_STEPS = ("Send this command in this session:\n\n  ! snaplogic auth login\n\n"
                 "Add --org <name> if you have more than one organization. "
                 "Then run /mcp to reconnect.")

# `or`, not a default: an empty CLAUDE_PLUGIN_ROOT falls back too, as in mcp_headers.py.
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)

# Credential relay: Claude Code >=2.1.238 strips credential-named env vars from the
# plugin's headersHelper (but NOT from this SessionStart hook), so the MCP helper can
# no longer read SNAPLOGIC_API_PASS from the environment. We capture it here, where it
# is still present, and write it to a fixed file the helper reads. Path is computed
# without any env var so the hook and the helper always agree on it. Not the
# `credentials` file earlier versions write beside it: sessions still running an
# earlier version after an update keep reading and writing that one, and the two
# formats would break each other.
CRED_FILE = Path(os.path.expanduser("~/.claude/snapcode/mcp-credentials.json"))


def write_credentials() -> None:
    """Record, for this session's deployment, which credential the MCP helper sends.

    Claude Code gives a plugin's headersHelper neither SNAPLOGIC_API_PASS nor anything
    that says which session it serves: only the MCP server's URL. This hook does see
    the session's environment, so it records in CRED_FILE what the session's own CLI
    uses for its deployment, and mcp_headers.py looks it up by the deployment it
    connects to:

    - a password in the environment: {"method": "password", "user", "pass"}. The CLI
      uses the password when one is set, even over a browser sign-in, and so does MCP.
    - no password: {"method": "token"}, which also drops a password an earlier session
      left for this deployment. Kept, that password is what MCP would fall back to
      whenever the browser sign-in lapsed, and every try of it counts toward the
      account's lockout.

    Deployments are kept apart, so sessions on two pods do not overwrite each other.
    Only the SessionStart hook writes: a launcher run from a terminal has that
    terminal's environment, not a Claude Code session's.

    CRED_FILE is {"deployments": {<deployment>: entry}}; a file of any other shape is
    replaced rather than read. Each write goes to a uniquely named temp file (0600
    on POSIX) that is renamed into place, and the read, the decision and the write
    run under _credential_lock(), so two session starts cannot lose each other's
    entries.

    CRED_FILE is a fixed path on purpose, computed without any env var so the hook
    and the helper always agree on it. That also means there is nothing to redirect:
    running this script by hand with SNAPLOGIC_API_USER and SNAPLOGIC_API_PASS set to
    test values overwrites the real relay for whoever is running it, and their MCP
    connection starts answering 401 until a session start writes it back.
    """
    if os.environ.get("SNAPCODE_FROM_LAUNCHER") or not SNAPLOGIC_BASE_URL:
        return
    user = os.environ.get("SNAPLOGIC_API_USER")
    pw = os.environ.get("SNAPLOGIC_API_PASS")
    entry = {"method": "password", "user": user, "pass": pw} if user and pw else {"method": "token"}
    # A Claude Code session keeps the environment it was started with. One started
    # before a password change still has the old password, and without this it
    # writes it back on its next resume or /clear, after which every session's MCP
    # on that deployment retries it and counts toward the account's lockout. So an
    # entry names the session that wrote it, and an earlier session does not
    # overwrite a later one's. Where the start time cannot be read (Windows has no
    # `ps`, and busybox's `ps` has no -p or lstart), the entry is written regardless.
    started = _claude_started_at()
    entry.update(base_url=SNAPLOGIC_BASE_URL, session_started_at=started)
    key = _deployment(SNAPLOGIC_BASE_URL)
    with _credential_lock():
        entries = _credential_entries()
        prev = entries.get(key, {}).get("session_started_at")
        if started is not None and isinstance(prev, (int, float)) and prev > started:
            log("credential file was written by a newer Claude Code session for this "
                "deployment; leaving it")
            return
        entries[key] = entry
        CRED_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, tmp = tempfile.mkstemp(dir=str(CRED_FILE.parent), prefix=".mcp-credentials.")
        try:
            with os.fdopen(fd, "w") as f:  # mkstemp created it 0600 on POSIX
                f.write(json.dumps({"deployments": entries}))
            os.replace(tmp, CRED_FILE)  # atomic
        finally:
            if os.path.exists(tmp):  # replace failed — don't leave the password in a stray temp file
                os.unlink(tmp)


def _credential_entries() -> dict:
    """CRED_FILE's entries by deployment, or {} for a missing file or one of any
    other shape."""
    try:
        d = json.loads(CRED_FILE.read_text())
    except FileNotFoundError:  # the first session start writes it
        return {}
    entries = d.get("deployments") if isinstance(d, dict) else None
    if not isinstance(entries, dict):
        return {}
    return {k: v for k, v in entries.items() if isinstance(v, dict)}


@contextlib.contextmanager
def _credential_lock():
    """Hold an exclusive lock beside CRED_FILE for the read-decide-write above.

    Without it two session starts can both read the file before either replaces
    it: the older one, deciding on what it read, replaces the newer one's password
    with its own, and a session on another deployment drops the entry the other
    one just wrote. Held for a few file operations, so it is waited for rather
    than timed out.

    Windows has no fcntl, so there two session starts at the same moment can still
    lose one entry, until that session's next start.
    """
    fd = None
    if fcntl is not None:
        CRED_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(CRED_FILE.parent / "mcp-credentials.lock"), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)  # closing releases the lock


def _claude_started_at() -> Optional[float]:
    """When the Claude Code process running this hook started, as epoch seconds.

    Claude Code puts its own pid in the hook's environment as CLAUDE_PID. None when
    that is missing or `ps` cannot answer, which callers treat as unknown.
    """
    pid = os.environ.get("CLAUDE_PID", "")
    if not pid.isdigit():
        return None
    try:
        r = subprocess.run(["ps", "-o", "lstart=", "-p", pid], capture_output=True,
                           text=True, timeout=5, env={**os.environ, "LC_ALL": "C"})
        return time.mktime(time.strptime(r.stdout.strip(), "%a %b %d %H:%M:%S %Y"))
    except FileNotFoundError:  # Windows has no ps
        return None
    except ValueError:  # busybox's ps has no -p or lstart and prints nothing
        return None


def _plugin_data_dir() -> Path:
    """Resolve the plugin's persistent data dir consistently across processes.

    Claude Code sets CLAUDE_PLUGIN_DATA when it runs the SessionStart hook, but NOT
    when the slpy launcher is invoked via the Bash tool — so if we fell back to
    PLUGIN_ROOT/.data (version-specific), the hook and the launcher would install/look
    for slpy in DIFFERENT dirs and re-install endlessly. Fall back to Claude Code's
    stable per-plugin data path (~/.claude/plugins/data/<plugin>-<marketplace>) so both
    processes agree. Both plugin and marketplace are named "snapcode" here.
    """
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env:
        return Path(env)
    stable = Path.home() / ".claude" / "plugins" / "data" / "snapcode-snapcode"
    if stable.parent.exists():  # normal installed layout
        return stable
    return PLUGIN_ROOT / ".data"  # last resort (e.g. --plugin-dir dev with no data dir)


PLUGIN_DATA = _plugin_data_dir()

TOOL_DIR = PLUGIN_DATA / "tools"        # where uv installs slpy
BIN_DIR = PLUGIN_DATA / "bin"           # where the slpy executable lands
LAST_CHECK = PLUGIN_DATA / "last_check"  # timestamp of last slpy check

# The installer endpoint lives on the SnapLogic SLServer:
#   {base_url}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer
# base_url = the user's pod (same host as the MCP endpoint), from the user's environment.
SNAPLOGIC_BASE_URL = os.environ.get("SNAPLOGIC_BASE_URL", "").rstrip("/")
# How often to check the index for a newer slpy (seconds). slpy publishes often, so a
# daily check keeps users current without a broker call every session.
CHECK_TTL = int(os.environ.get("SNAPCODE_CHECK_TTL", str(24 * 3600)))

# Note: the MCP auth helper (bin/mcp_headers.py) is referenced directly from .mcp.json
# via ${CLAUDE_PLUGIN_ROOT}, so bootstrap no longer copies it anywhere — that removes the
# first-session race where the MCP tried to connect before the helper was in place.

SLPY_EXE = BIN_DIR / ("slpy.exe" if os.name == "nt" else "slpy")


def log(msg: str) -> None:
    print(f"[snapcode-bootstrap] {msg}", file=sys.stderr)


# One-time welcome flag (shown only on the very first session after install).
WELCOME_FLAG = PLUGIN_DATA / ".welcomed"

def _skill_lines() -> str:
    names = sorted(d.name for d in (PLUGIN_ROOT / "skills").iterdir()
                   if (d / "SKILL.md").is_file())
    # The summarised ones first, in the order above, then anything newer.
    names.sort(key=lambda n: list(SKILL_SUMMARIES).index(n)
               if n in SKILL_SUMMARIES else len(SKILL_SUMMARIES))
    return "".join(f"      – {n}" + (f" — {SKILL_SUMMARIES[n]}" if n in SKILL_SUMMARIES else "")
                   + "\n" for n in names)


def welcome_text() -> str:
    return WELCOME.format(skills=_skill_lines().rstrip("\n"))


def no_address_note(slpy_installed: bool) -> str:
    return NO_ADDRESS_NOTE.format(cost=COST_SLPY_INSTALLED if slpy_installed else COST_NO_CLI)


def not_signed_in_note(slpy_installed: bool) -> str:
    return NOT_SIGNED_IN_NOTE.format(cost=COST_SLPY_INSTALLED if slpy_installed else COST_SLPY_MISSING,
                                     steps=SIGN_IN_STEPS)


def quiet_path_note() -> str:
    """The fix for a failed checklist item when this run had nothing to install.

    Every [x] in the checklist has its fix underneath. On this path slpy is
    present, so only the address and the sign-in can still be missing.
    """
    if not SNAPLOGIC_BASE_URL:
        return no_address_note(True)
    if env_basic_present():
        return ""
    return not_signed_in_note(True) if auth_state() == "out" else ""


def report(welcome: str, note: str = "") -> None:
    """The one message a run emits, to the user and to the model both.

    The note used to reach the model alone on every path except success, so a
    first run that failed showed a welcome and nothing about the failure, and
    only something that could see the model's context could say what went wrong.

    The welcome is marked shown here rather than where it is built, so a run
    that ends before this point has not spent it.
    """
    if os.environ.get("SNAPCODE_FROM_LAUNCHER"):
        # A launcher ran this to install what a command needs. Its stderr is what
        # the person or agent who ran the command reads, so it gets the note, as
        # plain text, and not the hook's JSON, the checklist or the command
        # surface, which are the session start's to show. The welcome is left
        # unspent for the next session start.
        if note:
            print(note, file=sys.stderr)
        return
    update, outdated = update_banner()
    if outdated:
        # Only the update: the checklist would describe a version about to be
        # replaced, and its fixes may not apply to the new one. The welcome stays
        # unspent; the new version shows its own on the session after the update.
        emit_to_user(update, update)
        return
    status = status_block()
    body = "\n\n".join(part for part in (update, welcome, status, note) if part)
    if welcome:
        WELCOME_FLAG.write_text((plugin_version() or "shown") + "\n")
    emit_to_user(body, "\n\n".join(part for part in (update, status, note, cli_command_surface()) if part))


def emit_to_user(system_message: str = "", model_context: str = "") -> None:
    """Emit a SessionStart hook JSON result. `systemMessage` is shown to the USER;
    `additionalContext` is injected for the model. Printed to stdout (SessionStart
    reads stdout); no-op if both are empty."""
    if not system_message and not model_context:
        return
    out = {}
    if system_message:
        out["systemMessage"] = system_message
    if model_context:
        out["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": model_context,
        }
    print(json.dumps(out))


def first_time() -> bool:
    """True on the first session of each plugin version. report() marks it shown.

    Keyed on the version so an update shows what changed. A flag from before
    this, which says only "shown", counts as a different version.
    """
    try:
        if WELCOME_FLAG.read_text().strip() == (plugin_version() or "shown"):
            return False
    except FileNotFoundError:  # never shown
        pass
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    return True


# ── timing ────────────────────────────────────────────────────────────────────
def check_due() -> bool:
    """True if we haven't checked the index within the TTL window."""
    if not SLPY_EXE.exists():
        return True  # not installed yet — must install
    if not LAST_CHECK.exists():
        return True
    last = float(LAST_CHECK.read_text().strip())
    return (time.time() - last) >= CHECK_TTL


def mark_checked() -> None:
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    LAST_CHECK.write_text(str(time.time()))


# ── HTTPS from the bare interpreter ───────────────────────────────────────────
# Identify the SnapCode plugin as a real client. Some pods (e.g. canary) sit behind
# Cloudflare bot protection that rejects the default Python-urllib User-Agent with a
# 1010 error; a proper UA identifies our legitimate client (like gh/aws CLIs do).
USER_AGENT = "snapcode-plugin-bootstrap/0.1 (+https://github.com/Snap-Developers/SnapCode-CC-Plugin)"



# What to tell the user when an HTTPS call fails TLS verification (as opposed to a real
# credentials/URL problem). Both onboarding failures we've seen (2026-08) were this: a
# python.org macOS Python whose CA bundle was never populated, mis-reported as a
# "credentials missing" error and sending people to chase config that was already correct.
TLS_TRUST_HINT = (
    "this is a TLS trust problem, NOT a credentials/URL problem — your Python has no "
    "usable CA trust store (common on python.org macOS builds where the bundled "
    "'Install Certificates.command' was never run), or a corporate proxy presents a "
    "custom root CA your Python can't see. Fix: run \"/Applications/Python 3.x/Install "
    "Certificates.command\" (macOS python.org build), or point Python at a CA bundle, e.g. "
    "export SSL_CERT_FILE=\"$(python3 -c 'import certifi; print(certifi.where())')\". "
    "See SnapCode setup docs."
)


# Set when the CLI download failed TLS certificate verification, so main() can emit the
# TLS hint at its final (most visible) exit point. Worth keeping after the move to the
# CLI: this is still the user's bare interpreter making an HTTPS call before any managed
# environment exists, which is exactly where the two failures below happen.
_TLS_TRUST_FAILURE = False

# The status the download endpoint answered with, when it answered at all.
# "Could not download" covers two situations a user acts on differently: a
# machine that cannot reach the host, and a host that replied with an error.
# Telling them apart matters, because the advice for the first one sends
# someone checking a VPN for a problem that is not on their machine.
_FETCH_HTTP_STATUS: Optional[int] = None


def _is_tls_trust_error(e: Exception) -> bool:
    """True if a urlopen failure was a TLS certificate-verification failure (vs. a real
    connectivity/auth error). urllib wraps the ssl error in URLError.reason.

    We match ssl.SSLCertVerificationError specifically (not any ssl.SSLError) — the two
    scenarios this targets (empty CA bundle, corporate proxy root) raise exactly that,
    while other SSLErrors (protocol mismatch, handshake EOF) are NOT trust problems and
    shouldn't send the user to run Install Certificates.command."""
    return (isinstance(e, ssl.SSLCertVerificationError)
            or isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError))


def _ssl_context() -> Optional[ssl.SSLContext]:
    """Build the SSL context for bootstrap's own HTTPS calls, tolerating a broken/empty
    default trust store.

    bootstrap runs on the user's own Python — BEFORE slpy's venv exists — so the default
    SSL context is whatever that bare interpreter ships. Two common breakages:
      • python.org macOS builds where "Install Certificates.command" was never run have an
        EMPTY OpenSSL cert bundle → every HTTPS call fails CERTIFICATE_VERIFY_FAILED.
      • a corporate SSL-inspection proxy presents a custom root CA that lives only in the
        OS trust store, which Python's default context doesn't read.

    Prefer, in order:
      1. truststore — use the OS native trust store (macOS Keychain / Windows cert store /
         Linux CA bundle). Covers BOTH cases above. Used only if importable.
      2. certifi's CA bundle — public roots; covers the empty-bundle case. If importable.
      3. None — Python's default context (today's behaviour; no regression).

    NOTE: this only affects the context object we build in-process for our own requests —
    it does NOT modify the user's machine (no cert.pem written, no env changed). And it
    NEVER disables verification: every branch still verifies certs, just against a valid
    trust source. truststore/certifi may be absent in the bare interpreter; when neither
    imports we fall through to the default and rely on the TLS_TRUST_HINT to guide the fix.
    """
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    return None


def _open_url(url: str, timeout: float):
    """urlopen with the plugin's User-Agent and trust store, for every HTTPS call here."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())


# ── the snaplogic CLI ─────────────────────────────────────────────────────────
# Where the published CLI artifacts live: the SLServer CLI-installer endpoint on the
# user's own control plane, which serves one flat current set of
# snaplogic_<os>_<arch> archives beside a checksums.txt covering all of them. Each
# control plane publishes its own build, so the CLI comes from the one the user
# works on.
CLI_ARTIFACT_BASE = (f"{SNAPLOGIC_BASE_URL}/api/1/rest/slserver/cli/installer"
                     if SNAPLOGIC_BASE_URL else "")

CLI_EXE = BIN_DIR / ("snaplogic.exe" if os.name == "nt" else "snaplogic")
# The CLI checks for and downloads its updates from the address in this file, the
# one install.sh records. Without it the CLI would update from canary's builds.
CLI_INSTALLER_MARKER = BIN_DIR / ".installer-base-url"


def _cli_asset_name() -> Optional[str]:
    """The published artifact for this machine, or None if we publish none."""
    import platform
    system = {"Darwin": "darwin", "Linux": "linux",
              "Windows": "windows"}.get(platform.system())
    arch = {"x86_64": "amd64", "amd64": "amd64",
            "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    if not system or not arch:
        return None
    suffix = "zip" if system == "windows" else "tar.gz"
    return f"snaplogic_{system}_{arch}.{suffix}"


def _artifact_url(name: str) -> str:
    """The URL that serves the artifact itself.

    Without `binary=true` the same path answers with JSON naming the file and a
    version, which is metadata about the upload rather than the file, so every
    caller here wants the query string.
    """
    return f"{CLI_ARTIFACT_BASE}/{name}?binary=true"


def _fetch(url: str) -> Optional[bytes]:
    """GET url, or None. Sets _TLS_TRUST_FAILURE so main() can say which failure it was."""
    global _TLS_TRUST_FAILURE, _FETCH_HTTP_STATUS
    try:
        with _open_url(url, timeout=60) as r:
            return r.read()
    except OSError as e:  # offline, proxy, TLS trust, or an HTTP error status
        if _is_tls_trust_error(e):
            _TLS_TRUST_FAILURE = True
            log(f"download failed ({url}): {e} — {TLS_TRUST_HINT}")
        else:
            if isinstance(e, urllib.error.HTTPError):
                _FETCH_HTTP_STATUS = e.code
            log(f"download failed ({url}): {e}")
        return None


def _extract_cli(archive: bytes, asset: str, dest: Path) -> bool:
    """Pull just the snaplogic binary out of the archive and put it at dest.

    One named member, never extractall: the archive is only as trustworthy as the
    host it came from, and a member called ../../something would otherwise be
    written wherever it asked.
    """
    import io
    want = {"snaplogic", "snaplogic.exe"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".{dest.name}.partial"
    try:
        if asset.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                name = next((n for n in z.namelist() if Path(n).name in want), None)
                if not name:
                    log(f"no snaplogic binary inside {asset}")
                    return False
                tmp.write_bytes(z.read(name))
        else:
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as t:
                member = next((m for m in t.getmembers()
                               if m.isfile() and Path(m.name).name in want), None)
                if not member:
                    log(f"no snaplogic binary inside {asset}")
                    return False
                tmp.write_bytes(t.extractfile(member).read())
        tmp.chmod(0o755)
        os.replace(str(tmp), str(dest))
        return True
    finally:
        if tmp.exists():
            tmp.unlink()


def ensure_snaplogic() -> Optional[Path]:
    """Return the path to the snaplogic CLI, downloading it if it is not here yet.

    No credentials: the artifacts are public, which is the point of fetching the
    binary rather than asking the user to install it.

    Only the first copy comes from here. After that the CLI updates itself in
    place, from the address in CLI_INSTALLER_MARKER, which is rewritten on every
    run so that switching control plane moves the updates with it.
    """
    if not CLI_ARTIFACT_BASE:
        return CLI_EXE if CLI_EXE.exists() else None
    if CLI_EXE.exists():
        CLI_INSTALLER_MARKER.write_text(CLI_ARTIFACT_BASE)
        return CLI_EXE

    asset = _cli_asset_name()
    if not asset:
        import platform
        log(f"no published snaplogic CLI for {platform.system()}/{platform.machine()}")
        return None

    sums = _fetch(_artifact_url("checksums.txt"))
    blob = _fetch(_artifact_url(asset)) if sums else None
    if not blob:
        return None

    import hashlib
    expected = ""
    for line in sums.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == asset:
            expected = parts[0]
            break
    actual = hashlib.sha256(blob).hexdigest()
    if not expected or expected != actual:
        # Refuse rather than run it. A mismatch is either a corrupted download or
        # something worse, and neither is a thing to execute.
        log(f"checksum mismatch for {asset} (expected {expected or 'nothing'}, got {actual})")
        return None

    if not _extract_cli(blob, asset, CLI_EXE):
        return None
    CLI_INSTALLER_MARKER.write_text(CLI_ARTIFACT_BASE)
    log(f"snaplogic CLI ready at {CLI_EXE}")
    return CLI_EXE


def _tail(text: str, limit: int = 6) -> str:
    lines = [ln for ln in (text or "").strip().splitlines() if ln.strip()]
    return "\n".join(lines[-limit:])


def _run_cli(args, extra_env=None, timeout=30):
    """Run the CLI and return (returncode, stdout, stderr). Never raises.

    The default suits a question, not a job. An install builds a Python
    environment from scratch and can take minutes on a cold machine or a slow
    link, and this bootstrap is re-run by the slpy launcher where nothing else
    would cut it short, so cutting it short here would be the only thing stopping
    it from finishing.
    """
    env = dict(os.environ)
    # Present but empty is the user opting out, so only an unset one is filled in.
    env.setdefault("SNAPLOGIC_CLIENT", client_token())
    if extra_env:
        env.update(extra_env)
    try:
        r = subprocess.run([str(CLI_EXE)] + args, env=env, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    # A CLI that hangs, or a binary built for another machine ("Exec format error"),
    # which cli_state() reports as broken.
    except (subprocess.TimeoutExpired, OSError) as e:
        return 1, "", str(e)


def cli_state() -> str:
    """'ok', 'old', or 'broken'.

    Asked rather than assumed, because the artifact host serves whatever was last
    published with no version in the URL, so there is nothing to pin: a binary cut
    before `snaplogic slpy` landed is a state that happens.

    Two probes, not one, because a binary that cannot run at all fails the second
    probe exactly like an old one does, and telling someone their CLI is out of
    date when it is really the wrong architecture sends them to wait for a release
    that will not help.
    """
    if _run_cli(["--version"])[0] != 0:
        return "broken"
    return "ok" if _run_cli(["slpy", "--help"])[0] == 0 else "old"


def auth_state() -> str:
    """'in', 'out', or 'unknown'. Callers check SNAPLOGIC_BASE_URL first.

    'unknown' is the CLI failing to answer a question it was asked, which is not a
    reason to tell anyone to sign in.

    `auth status` exits 0 whether or not anyone is signed in, by design: not signed
    in is a valid answer, not a failure to answer. So the answer is in the JSON, and
    a non-zero exit means something else went wrong, which is a different thing and
    must not be reported to the user as "please sign in".
    """
    entry = _auth_status().entry
    if entry is None:
        return "unknown"
    return "in" if entry.get("logged_in") else "out"


class AuthStatus(NamedTuple):
    """One call to `snaplogic auth status --json`, for SNAPLOGIC_BASE_URL.

    entry: what the CLI reports for this address (password or saved login), or None.
    notes: the CLI's "Note:" lines, where the environment disagrees with the saved login.
    error: the CLI's message when it refused to answer.
    """
    entry: Optional[dict]
    notes: Tuple[str, ...]
    error: str


@functools.lru_cache(maxsize=None)
def _auth_status() -> AuthStatus:
    """`snaplogic auth status --json` for SNAPLOGIC_BASE_URL; see AuthStatus.

    The one place that reads `auth status`, for the sign-in decision and for the
    checklist alike, and read once per run, so the two cannot disagree about what
    the CLI said and a CLI that hangs costs one timeout, not one per reader. Once
    is enough: every reader comes after the CLI is in place, and nothing in a run
    signs in or out.
    """
    if not SNAPLOGIC_BASE_URL:
        return AuthStatus(None, (), "")
    # The CLI reads SNAPLOGIC_BASE_URL from the environment it inherits.
    report, err = _cli_json(["auth", "status", "--json"])
    notes = tuple(text[len("Note: "):].strip() for text in err.splitlines() if text.startswith("Note: "))
    if report is None:
        return AuthStatus(None, notes, _cli_error(err))
    # Only the entry for this address: one for another control plane says nothing
    # about whether this session, which is on SNAPLOGIC_BASE_URL, is signed in.
    want = _deployment(SNAPLOGIC_BASE_URL)
    for entry in report:
        if _deployment(entry["base_url"]) == want:
            return AuthStatus(entry, notes, "")
    return AuthStatus(None, notes, "")


def _cli_error(stderr: str) -> str:
    """The message in the {"error": ...} the CLI writes to stderr under --json, or "".
    A failed slpy install writes it after uv's output, so it is found, not parsed whole."""
    found = re.search(r'\{\s*"error"', stderr)
    if not found:
        return ""
    return json.JSONDecoder().raw_decode(stderr[found.start():])[0]["error"]


def env_basic_present() -> bool:
    """A username and password in the environment is still a way to be authenticated,
    and the way nearly every current user is. They must never be told to sign in."""
    return bool(os.environ.get("SNAPLOGIC_API_USER") and os.environ.get("SNAPLOGIC_API_PASS"))


def install_slpy() -> Tuple[bool, str]:
    """Install or update slpy through the CLI.

    --bin-dir keeps the executables exactly where the plugin's slpy launcher already
    looks, so nothing about `slpy ...` from the agent changes. UV_TOOL_DIR is
    inherited by uv through the CLI and keeps the environment in the plugin's own
    data dir: left at uv's default, the plugin's daily --force install and the
    user's own `uv tool` commands would write to the same environment.
    """
    rc, out, err = _run_cli(
        ["slpy", "install", "--json", "--bin-dir", str(BIN_DIR)],
        extra_env={"UV_TOOL_DIR": str(TOOL_DIR)},
        timeout=600,
    )
    if rc == 0:
        return True, json.loads(out).get("version", "")
    # The two streams split by outcome, not by format: --json writes the result to
    # stdout and the reason for a failure to stderr, alongside uv's own progress
    # noise. So a failure is read from stderr, and only the sentence inside is worth
    # showing -- the raw object is not something to put in front of a user.
    message = _cli_error(err)
    if message:
        return False, message
    return False, _tail(err) or f"the CLI exited with status {rc}"


# ── plugin updates ──────────────────────────────────────────────────────────
# A marketplace added from GitHub does not update itself unless the user turns on
# auto-update, so this is the only place a customer learns a release is out.
# Public `main` carries only released builds, so its plugin.json is the latest
# release. Checked every session: the timeout is short, and a failed check
# only hides the version part of the banner. To test the banner, point
# SNAPCODE_LATEST_PLUGIN_JSON at another plugin.json (a file:// URL works).
LATEST_PLUGIN_JSON = (
    os.environ.get("SNAPCODE_LATEST_PLUGIN_JSON")
    or "https://raw.githubusercontent.com/Snap-Developers/SnapCode-CC-Plugin/main/plugin/.claude-plugin/plugin.json"
)
LATEST_CHECK_TIMEOUT = 3

CLAUDE_CONFIG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
PLUGIN_CACHE = CLAUDE_CONFIG / "plugins" / "cache"
# Claude Code's record of each marketplace: where it is installed, and the
# /plugin auto-update toggle.
KNOWN_MARKETPLACES = CLAUDE_CONFIG / "plugins" / "known_marketplaces.json"
USER_SETTINGS = CLAUDE_CONFIG / "settings.json"


def installed_from_marketplace() -> bool:
    """Whether this copy was installed with `claude plugin install`.

    True for any install from the snapcode marketplace, whichever repo it was
    added from: the plugin then runs from Claude Code's plugin cache, or from the
    marketplace's own folder when the marketplace is a local directory.

    False under `claude --plugin-dir <checkout>`, so a developer sees no update
    banner or tip: a checkout is ahead of or behind the release on purpose, and
    has no marketplace to turn auto-update on for.
    """
    homes = [PLUGIN_CACHE]
    try:
        homes.append(Path(json.loads(KNOWN_MARKETPLACES.read_bytes())["snapcode"]["installLocation"]))
    # What `claude --plugin-dir` leaves: no marketplace added at all (OSError), or
    # others but not snapcode (KeyError).
    except (OSError, KeyError):
        pass
    root = PLUGIN_ROOT.resolve()
    return any(root == home or home in root.parents for home in (h.resolve() for h in homes))


def latest_plugin_version() -> str:
    """The released version, or "" when it cannot be read in time.

    Not _fetch(): that one waits a minute and records its failure for the CLI
    download's error message, which this check must not touch.
    """
    try:
        with _open_url(LATEST_PLUGIN_JSON, timeout=LATEST_CHECK_TIMEOUT) as r:
            return json.loads(r.read()).get("version", "")
    except OSError as e:  # offline, or GitHub is slow to answer
        log(f"could not read the latest plugin version: {e}")
        return ""


def _version_key(version: str) -> Optional[Tuple[int, ...]]:
    try:
        return tuple(int(part) for part in version.lstrip("vV").split("."))
    except ValueError:  # "", when the latest version could not be read
        return None


def auto_update_on() -> bool:
    """Whether Claude Code will update the snapcode marketplace by itself.

    The /plugin toggle is stored in known_marketplaces.json, and Claude Code
    copies `autoUpdate` from the user's settings.json there at startup. Both are
    read so the answer does not depend on which of the two ran first.
    """
    sources = (
        (KNOWN_MARKETPLACES, lambda d: d.get("snapcode", {})),
        (USER_SETTINGS, lambda d: d.get("extraKnownMarketplaces", {}).get("snapcode", {})),
    )
    for path, entry in sources:
        try:
            data = json.loads(path.read_bytes())
        # OSError: no settings.json, which most users do not have. ValueError: one
        # with a typo, since install-snapcode.md has users edit it by hand and Claude Code
        # starts anyway.
        except (OSError, ValueError):
            continue
        if entry(data).get("autoUpdate") is True:
            return True
    return False


def update_banner() -> Tuple[str, bool]:
    """What to show above everything else, and whether to show only that.

    A plugin the user can update right now is fixed by updating, not by working
    through a checklist of the old version, so that case shows nothing else.
    With auto-update on, Claude Code installs the new version within ten minutes
    of the next message, so the session carries on as usual until then.
    """
    if not installed_from_marketplace():
        return "", False
    auto = auto_update_on()
    current, latest = plugin_version(), latest_plugin_version()
    current_key, latest_key = _version_key(current), _version_key(latest)
    behind = bool(current_key and latest_key and latest_key > current_key)

    if behind and auto:
        return UPDATE_AVAILABLE_AUTO.format(latest=latest, current=current), False
    if behind:
        return UPDATE_AVAILABLE.format(latest=latest, current=current), True
    return ("" if auto else AUTO_UPDATE_TIP), False


# ── status ──────────────────────────────────────────────────────────────────
def plugin_version() -> str:
    # Bytes, not read_text(): that decodes with the Windows code page (GBK on a
    # Chinese system), which fails on the description's em dash and hides the
    # version. json.loads detects UTF-8, with or without a BOM, by itself.
    return json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_bytes()).get("version", "")


# SnapCode's calls to the CLI carry SNAPLOGIC_CLIENT, which the CLI appends to its
# User-Agent, so the platform can tell them from someone running the CLI by hand.
# It is set on the calls themselves, as the MCP helper sets X-MCP-Tool-Profile on
# its requests, rather than in the user's settings: nothing of the user's is
# written, and the first session is tagged too.
CLIENT_TOKEN_FILE = PLUGIN_DATA / "client_token"


def client_token() -> str:
    version = plugin_version()
    return f"snapcode/{version}" if version else "snapcode"


def write_client_token() -> None:
    """For the launchers. Parsing plugin.json in sh and cmd is not worth it when
    this already knows the answer and runs every session."""
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    CLIENT_TOKEN_FILE.write_text(client_token() + "\n")


def _help_commands(help_text: str) -> list:
    """The first word of each line under 'Available Commands:', up to 'Flags:'."""
    commands, inside = [], False
    for ln in help_text.splitlines():
        if ln.startswith("Available Commands:"):
            inside = True
        elif ln.startswith("Flags:"):
            inside = False
        elif inside and ln.strip():
            commands.append(ln.split()[0])
    return commands


def cli_command_surface() -> str:
    """The CLI's commands on this install, for the model (DSAI-1463).

    The snaplogic-deploy skill must not assume a subcommand exists just because
    its examples use one: the CLI ships commands independently of the skill. Run
    here rather than in a hook of its own because hooks run side by side, and on
    a first session this is the run that downloads the CLI. Local and about 80 ms.
    Anything that fails leaves it out rather than holding up the session.
    """
    if not CLI_EXE.exists():
        return ""
    rc, top, _ = _run_cli(["--help"], timeout=10)
    groups = _help_commands(top) if rc == 0 else []
    if not groups:
        return ""
    parts = [
        "## MANDATORY: snaplogic CLI command availability (this session)",
        "",
        "The snaplogic CLI on this machine supports these command groups right now:",
        "",
        "\n".join(f"- {g}" for g in groups),
        "",
        "RULE — not a suggestion: never assume a `snaplogic` subcommand from the",
        "snaplogic-deploy skill's examples exists just because it's written there — the",
        "CLI ships new commands independently of that skill. Check the full command",
        "surface below (or re-run `snaplogic <group> --help`) before relying on any",
        "subcommand this skill's workflow calls for.",
        "",
        "## Full discovered command surface (reference)",
        "",
        "```",
        top.strip(),
        "```",
    ]
    for group in groups:
        _, out, err = _run_cli([group, "--help"], timeout=10)
        parts += ["", f"### snaplogic {group} --help", "```", ((out or "") + (err or "")).strip(), "```"]
    return "\n".join(parts)


def _cli_json(args, extra_env=None) -> Tuple[Optional[object], str]:
    """A CLI answer parsed from its --json output, or None when there is no CLI or
    it exits non-zero, and the CLI's stderr, which says why when there is no answer.
    Only local questions are asked here.
    """
    if not CLI_EXE.exists():
        return None, ""
    rc, out, err = _run_cli(args, extra_env=extra_env, timeout=10)
    if rc != 0:
        return None, err
    return json.loads(out), err


def _deployment(url: str) -> str:
    """The deployment an address names, as the snaplogic CLI and mcp_headers.py key
    it: lowercase host, and cdn.<host> is <host> behind Cloudflare. mcp_headers.py's
    must give the same key, so change both together."""
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    return host[len("cdn."):] if host.startswith("cdn.") else host


def _has_browser_sign_in(entry: dict) -> bool:
    """Whether `auth status` reports a usable stored token, which is what the MCP
    helper sends when this deployment's entry is not a password. A CLI from before
    DSAI-1920 reports only the token, as logged_in; a later one reports the
    credential in use, and says when the environment's password shadows a valid
    token."""
    if "method" in entry:
        return entry.get("method") == "token" or bool(entry.get("stored_token_ignored"))
    return bool(entry.get("logged_in"))


def status_block() -> str:
    """Where each part of the plugin stands, shown on every session start.

    Everything here is local: the CLI's own view of what is installed and who is
    signed in, and the environment. Nothing reaches the platform, because a
    check sent with a wrong password counts toward the account's lockout, and
    that is also why the MCP server is reported as configured rather than
    connected: whether it connected is Claude Code's to say, in /mcp. What to do
    about a failed item is the note's job, underneath.
    """
    lines = []

    def line(ok: bool, text: str) -> None:
        lines.append(("  [ok] " if ok else "  [x]  ") + text)

    cli = ""
    if CLI_EXE.exists():
        rc, out, _ = _run_cli(["--version"], timeout=10)
        cli = out.strip().rsplit(" ", 1)[-1] if rc == 0 and out.strip() else ""
    line(bool(cli), CHECK_CLI.format(version=cli) if cli else CHECK_CLI_MISSING)

    # Sign-in, then slpy: slpy is installed through the sign-in, so this order puts
    # the first thing to fix first.
    host = SNAPLOGIC_BASE_URL.split("://", 1)[-1] if SNAPLOGIC_BASE_URL else ""
    entry, notes, error = _auth_status()
    if not SNAPLOGIC_BASE_URL:
        line(False, CHECK_SIGN_IN_NO_ADDRESS)
    elif error:
        line(False, CHECK_SIGN_IN_CLI_SAYS.format(message=error))
    elif entry is None:
        line(False, CHECK_SIGN_IN_NO_ANSWER)
    elif notes:
        # The CLI found the environment and the saved login at odds, and its commands
        # stop until that is fixed, so the notes replace the [ok].
        for note in notes:
            line(False, CHECK_SIGN_IN_CLI_SAYS.format(message=note))
    elif entry.get("method") == "basic":
        line(True, CHECK_SIGN_IN_PASSWORD.format(user=entry["user"]))
    elif entry.get("logged_in") and entry.get("user"):
        line(True, CHECK_SIGN_IN_BROWSER.format(user=entry["user"]))
    elif entry.get("logged_in"):
        line(True, CHECK_SIGN_IN_BROWSER_NO_USER)
    else:
        line(False, CHECK_SIGN_IN_OUT.format(host=host))

    slpy, err = _cli_json(["slpy", "status", "--json"], extra_env={"UV_TOOL_DIR": str(TOOL_DIR)})
    slpy, slpy_error = slpy or {}, _cli_error(err)
    if slpy.get("installed") and slpy.get("version"):
        line(True, CHECK_SLPY.format(version=slpy["version"]))
    elif slpy.get("installed") or SLPY_EXE.exists():
        line(True, CHECK_SLPY_INSTALLED)
    elif slpy_error:
        line(False, CHECK_SLPY_CLI_SAYS.format(message=slpy_error))
    else:
        line(False, CHECK_SLPY_MISSING)

    # What mcp_headers.py will send: this deployment's entry, as write_credentials()
    # left it, and a browser sign-in's token when that entry is not a password.
    mcp = _credential_entries().get(_deployment(SNAPLOGIC_BASE_URL), {}) if SNAPLOGIC_BASE_URL else {}
    if not SNAPLOGIC_BASE_URL:
        line(False, CHECK_MCP_NO_ADDRESS)
    elif mcp.get("method") == "password" and env_basic_present():
        line(True, CHECK_MCP_PASSWORD.format(host=host))
    elif mcp.get("method") == "password":
        line(True, CHECK_MCP_SAVED_PASSWORD.format(host=host))
    elif entry is not None and _has_browser_sign_in(entry):
        line(True, CHECK_MCP_BROWSER.format(host=host))
    else:
        line(False, CHECK_MCP_NOT_SIGNED_IN)

    skills = sorted(d.name for d in (PLUGIN_ROOT / "skills").iterdir() if (d / "SKILL.md").is_file())
    skills.sort(key=lambda n: list(SKILL_SUMMARIES).index(n)
                if n in SKILL_SUMMARIES else len(SKILL_SUMMARIES))
    line(bool(skills), CHECK_SKILLS.format(count=len(skills), names=", ".join(skills))
         if skills else CHECK_SKILLS_NONE)

    return CHECKLIST_TITLE.format(version=plugin_version()).replace("  ", " ") + "\n" + "\n".join(lines)


# ── main ───────────────────────────────────────────────────────────────────--
def main() -> int:
    # Tell the MCP headersHelper which credential this deployment's MCP uses: Claude
    # Code >=2.1.238 no longer passes credential env vars to a plugin's
    # headersHelper, so a password reaches it only through this file. First, so it
    # runs even when the slpy check short-circuits.
    write_credentials()
    #
    # A hook can only emit one JSON result, so one message is collected and emitted
    # at the end. Two independent parts:
    #   - welcome: the first session ever (WELCOME_FLAG)
    #   - a note: only when something actually happened this run
    welcome = welcome_text() if first_time() else ""

    # The launchers read this to tag the CLI calls made in the session.
    write_client_token()

    # slpy present and checked within the window → stay quiet.
    if not check_due():
        # The CLI is still fetched here when it is missing: an install from before
        # the plugin used the CLI has a fresh slpy and no CLI, and the `snaplogic`
        # launcher, which runs this bootstrap to get one, would otherwise wait a
        # whole slpy window for it.
        ensure_snaplogic()
        log(f"slpy present and checked within {CHECK_TTL // 3600}h — skipping")
        report(welcome, quiet_path_note())
        return 0

    if not SNAPLOGIC_BASE_URL:
        # The CLI is downloaded from this address, so nothing below can run.
        log("no SnapLogic address configured")
        report(welcome, no_address_note(False))
        return 0

    if not ensure_snaplogic():
        if _TLS_TRUST_FAILURE:
            hint = TLS_TRUST_HINT
        elif _FETCH_HTTP_STATUS is not None:
            # Reached it and it refused. Nothing on this machine to check.
            hint = (f"{CLI_ARTIFACT_BASE} answered HTTP {_FETCH_HTTP_STATUS}. "
                    "That is the download service, not your machine or network.")
        else:
            hint = ("the CLI could not be downloaded. Check network access to "
                    f"{CLI_ARTIFACT_BASE}.")
        log(f"snaplogic CLI unavailable: {hint}")
        report(welcome, "Warning: could not set up the slpy CLI — " + hint)
        return 0

    state = cli_state()
    if state == "broken":
        log("the downloaded snaplogic CLI will not run on this machine")
        report(welcome, "Warning: the `snaplogic` CLI was downloaded but will not "
                              "run on this machine, so the slpy CLI was not installed. "
                              f"It came from {CLI_ARTIFACT_BASE}.")
        return 0
    if state == "old":
        # The artifact host serves whatever was published last, with no version in
        # the URL, so this is a real state and not a should-never-happen.
        log("the published snaplogic CLI predates `snaplogic slpy` — cannot install slpy")
        report(welcome, "Warning: the published `snaplogic` CLI is older than the "
                              "plugin expects and cannot install slpy. This needs a newer "
                              "CLI release; nothing to fix on your machine.")
        return 0

    signed = auth_state()
    if signed == "out" and not env_basic_present():
        # Sign-in opens a browser and waits for a person, which a SessionStart hook
        # cannot do: it is non-interactive and killed at 60s. So it asks, and the
        # slpy launcher re-runs this bootstrap on the first `slpy` call, which is
        # what lets the same session recover once the user has signed in.
        log("not signed in and no Basic credentials in the environment")
        report(welcome, not_signed_in_note(False))
        return 0

    # ~20s on a first run, which is long enough to look like a hang if nothing says so.
    log("installing/updating slpy through the snaplogic CLI…")
    ok, detail = install_slpy()
    if ok:
        mark_checked()
        log(f"done. slpy ready at {SLPY_EXE}")
        report(welcome)
        return 0

    if _TLS_TRUST_FAILURE:
        log(f"slpy not installed: {TLS_TRUST_HINT}")
        report(welcome, "Warning: could not install the slpy CLI — " + TLS_TRUST_HINT)
        return 0

    log(f"slpy install failed: {detail}")
    report(welcome, "Warning: could not install the slpy CLI. The CLI reported:"
                    f"\n\n```\n{detail}\n```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
