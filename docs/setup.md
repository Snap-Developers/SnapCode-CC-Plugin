# SnapCode — Setup

Install SnapCode as a single Claude Code plugin. No repo to clone, no container,
no GitHub or AWS account.

## 1. Prerequisites

Install these on your machine first:

| Tool | Why | Check |
|---|---|---|
| **Claude Code CLI** (v2.1.195+) | Runs the plugin; must support plugin marketplaces | `claude --version` |
| **Python 3.8+** | Runs the plugin's bootstrap + auth helper | `python3 --version` (macOS) / `python --version` (Windows) |

> **macOS uses `python3`; Windows uses `python`** (on Windows `python3` is often a Microsoft
> Store stub that isn't a real interpreter). The plugin discovers whichever one works, so
> either is fine as long as one of them runs Python 3.

### Install or update the Claude Code CLI

Don't have it yet? Install it —

macOS / Linux / WSL:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Windows PowerShell:
```powershell
irm https://claude.ai/install.ps1 | iex
```
(Or on any platform via npm: `npm install -g @anthropic-ai/claude-code`.)

Already have it? Plugin marketplaces need **v2.1.195 or later**. Native installs
auto-update; to update now:
```bash
claude update
```
(Homebrew: `brew upgrade claude-code` · npm: `npm install -g @anthropic-ai/claude-code@latest`.)

Check your version with `claude --version` (prints `X.Y.Z (Claude Code)`). If
`claude plugin …` isn't recognized or the version is below 2.1.195, update first.

## 2. Set your SnapLogic credentials (in your environment)

SnapCode authenticates to the SnapLogic cloud with **your existing SnapLogic
credentials** — set them as environment variables in your own shell. These are
SnapLogic platform credentials, **not** GitHub or AWS.

### What to set

| Variable | What it is |
|---|---|
| `SNAPLOGIC_API_USER` / `SNAPLOGIC_API_PASS` | Your SnapLogic platform login (email + password). Also authenticates the SnapLogic MCP server. |
| `SNAPLOGIC_BASE_URL` | Your pod URL — the same host you use for the SnapLogic UI. |
| `SNAPLOGIC_ORG_NAME` | Your SnapLogic organization name — usually your company/team name. Required to install the `slpy` CLI. If you're not sure of the exact name, ask your SnapLogic admin. |

> Set these **before** starting Claude Code. If you change any later, restart Claude Code.

Now set them for your platform:

### 2a. macOS / Linux

Add these lines to your shell profile — `~/.zshrc` on macOS, or `~/.bashrc` on most
Linux — so they **persist** across terminals, instead of a one-time `export` that's lost
when you close the window:

```bash
export SNAPLOGIC_API_USER='you@yourcompany.com'
export SNAPLOGIC_API_PASS='your-password'
export SNAPLOGIC_BASE_URL='https://your-pod.snaplogic.com'
export SNAPLOGIC_ORG_NAME='your-org-name'
```

Single quotes keep the values literal, so a `$`, `!`, `\`, or backtick in your password
won't be expanded by the shell. (If the password itself contains a single quote, use
`'pa'\''ss'` for `pa'ss`.)

After saving, run `source ~/.zshrc` (or open a new terminal) so the values load — then
start Claude Code from that shell. Child processes inherit the environment at launch, so
restart Claude Code / your editor if it was already open.

### 2b. Windows (PowerShell)

Set them at the User level so they **persist** and new terminals see them:

```powershell
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', 'you@yourcompany.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_PASS', 'your-password', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_BASE_URL', 'https://your-pod.snaplogic.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_ORG_NAME', 'your-org-name', 'User')
```

Single-quoted values stay literal, so a `$` or backtick in your password isn't treated as
a PowerShell variable/escape (if the password contains a single quote, double it:
`'pa''ss'`).

Windows has no `source` equivalent: after `SetEnvironmentVariable`, the **current** window
won't see the values — **open a new terminal** (and restart Claude Code / your editor,
since child processes inherit the environment at launch). Verify with
`[Environment]::GetEnvironmentVariable("SNAPLOGIC_ORG_NAME", "User")`.

## 3. Install the plugin

Run these two commands:

```bash
claude plugin marketplace add Snap-Developers/SnapCode-CC-Plugin
claude plugin install snapcode@snapcode
```

### First run

From your working directory, with your credentials (step 2) set, just start Claude Code:

```bash
claude
```

On every session the plugin:
- loads the SnapCode skills,
- connects to the SnapLogic MCP server using your credentials from step 2,
- has the `slpy` CLI ready.

To connect, an auth helper that ships inside the plugin authenticates to the SnapLogic MCP
server with your credentials (no install step, so it's ready on the **first** session). The
`slpy` CLI is installed on the first session by the SessionStart bootstrap; if you happen to
run `slpy` before that finishes, the launcher installs it on demand. If the MCP server shows
as not connected, see Troubleshooting below (usually a credential or variable-name issue).

### Updating

The plugin is a snapshot cloned locally — it does **not** auto-update. New plugin versions
ship with SnapLogic's monthly platform release, so updating once per release cycle keeps you
current on skills and fixes. To pull the latest, run these two commands (the first fetches the
latest from the repo, the second applies it):

```bash
claude plugin marketplace update snapcode
claude plugin update snapcode@snapcode
```

> The `slpy` CLI is separate: the plugin refreshes it on its own (a daily check against
> the private index), so you don't need to update it by hand.

## 4. Verify

Confirm the two pieces are working. First, check the SnapLogic MCP server is connected:

```bash
claude mcp list
```

Expected: `snapcode:snaplogic` is listed and shows **Connected**.

Then, inside a Claude Code session, confirm the `slpy` CLI is on PATH and runs:

```
! which slpy
! slpy --help
```

Expected: `which slpy` points inside the SnapCode plugin cache (not an old
`~/.local/bin/slpy`), and `slpy --help` prints the CLI usage instead of "command not found".

Finally, ask Claude to list snaps or generate a pipeline — it should use the SnapLogic MCP
server tools and the `slpy` CLI to do it.

## 5. Uninstall

```bash
claude plugin uninstall snapcode@snapcode
claude plugin marketplace remove snapcode
```

Those two commands remove the plugin and the marketplace entry. To also clear the bits
the plugin wrote outside its own directory (safe to delete — regenerated on reinstall; this
is the installed `slpy`, which can be large):

macOS / Linux:
```bash
rm -rf ~/.claude/plugins/cache/snapcode
```
Windows (PowerShell):
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\snapcode"
```

If you set the `SNAPLOGIC_*` env vars (step 2) and no longer want them:
- macOS / Linux: remove those `export` lines from `~/.zshrc` / `~/.bashrc`.
- Windows PowerShell: clear each User-level var, e.g.
  `[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', $null, 'User')` (repeat per variable).

## Optional: use SSO (OAuth) for the MCP server

> **Opt-in.** HTTP Basic remains the default — nothing below changes unless you set the
> variable. This applies to the **MCP server only**: the `slpy` installer still
> authenticates with `SNAPLOGIC_API_USER`/`SNAPLOGIC_API_PASS` over HTTP Basic, so keep
> those set even in OAuth mode.

On a pod whose MCP endpoint fronts the SnapLogic authorization server, Claude Code can sign
you in through the browser instead of sending your password on every request. Set one extra
variable:

macOS / Linux:
```bash
export SNAPLOGIC_AUTH_MODE=oauth
```
Windows (PowerShell):
```powershell
[Environment]::SetEnvironmentVariable('SNAPLOGIC_AUTH_MODE', 'oauth', 'User')
```

With that set, the auth helper emits no `Authorization` header. The server answers `401`
with an RFC 9728 `WWW-Authenticate` challenge carrying a `resource_metadata` pointer, and
Claude Code follows it into its own OAuth flow. Unset the variable — or set it to `basic` —
to go straight back to HTTP Basic.

### Trying it on a test pod

`SNAPLOGIC_BASE_URL` already parameterises the MCP URL, so pointing at another pod needs no
code change:

```bash
export SNAPLOGIC_BASE_URL='https://<your-test-pod>'
export SNAPLOGIC_AUTH_MODE=oauth
claude mcp list
```

Expected: `! Needs authentication`. Complete the browser sign-in with `/mcp` inside Claude
Code.

If you'd rather not touch the plugin's configuration at all, register the endpoint directly
as a separate server:

```bash
claude mcp add --transport http snaplogic-oauth \
  "$SNAPLOGIC_BASE_URL/api/1/rest/public/platform_mcp/mcp"
```

A server added this way has no header helper, so Claude Code goes to OAuth immediately.
Remove it afterwards with `claude mcp remove snaplogic-oauth`.

### Reading the result

| `claude mcp list` says | What it means |
|---|---|
| `! Needs authentication` | No header was sent and the server issued its OAuth challenge. **This is the success signal for OAuth mode** — finish sign-in with `/mcp`. |
| `✗ Failed to connect` | A header *was* sent and rejected — you're still on Basic, with credentials the server didn't accept. |
| `✓ Connected` | The server accepted the request. Weak evidence on its own — see below. |

> **`✓ Connected` does not prove authentication worked.** The health check only performs the
> MCP `initialize` call, and this endpoint answers `initialize` with a clean `200` and a
> valid `result` even when the credentials are wrong. The only sound proof is a `tools/list`
> that returns a **non-empty `tools` array** — ask Claude to list SnapLogic tools.

### Gotchas when testing the flow by hand

- **No trailing slash** on the endpoint — `.../platform_mcp/mcp/` returns `404`.
- **Never send an `Authorization` header to `/token`.** Any header there is a hard `400
  invalid_client`; the `client_id` belongs in the request body. (This is deliberate — Basic
  at `/token` would route into the platform password policy and risk locking the account.)
- **Omit `scope` at `/token`.** A scope that differs from the one granted yields
  `invalid_scope`.
- **Register and present `127.0.0.1`, never `localhost`.** The loopback *port* may float
  (RFC 8252 §7.3), but the host literal is compared exactly. At `/token`, echo back the
  **exact** `redirect_uri` string you sent to `/authorize` — port included — not the
  portless form you registered.
- **Authorization codes are short-lived.** A slow sign-in or a debugger breakpoint between
  callback and exchange yields `invalid_grant`; just restart the flow.
- **Don't assert on the HTTP status or the JSON-RPC `error` code.** With a bad bearer,
  `initialize` returns `200` with no `error` member at all, and `tools/list` returns `200`
  with `{"code": 0, ...}` — and `0` is **falsy**, so `if err["code"]:` silently passes.
  Assert on a non-empty `tools` array instead.
- **Retry `tools/list` before calling it an auth failure.** A test pod without MCP session
  affinity returns `404 Session not found` for a perfectly valid session a fair fraction of
  the time, because requests land on different upstreams. That's load balancing, not auth —
  single-shot `curl` tests will look randomly broken.
- **Cursor cannot complete this flow.** Its dynamic client registration presents a custom
  `cursor://` redirect scheme, which the server rejects with `400 invalid_client_metadata`.
  Claude Code and Claude Connectors are fine.

## Migrating from the old install (clone + Docker)

If you previously used the old SnapCode distribution (cloned the repo, ran the Docker
image, installed slpy/MCP globally), remove those first — they **conflict** with the
plugin:

Remove the old user-scope `snaplogic` MCP and the old `slpy` shim on PATH.

macOS / Linux:
```bash
claude mcp remove snaplogic
rm ~/.local/bin/slpy
```
Windows (PowerShell):
```powershell
claude mcp remove snaplogic
Remove-Item "$env:USERPROFILE\.local\bin\slpy*"
```

> **Note:** If you skip this, you'll have two SnapLogic MCPs registered — the old `snaplogic`
> and the plugin's `snapcode:snaplogic`. They don't share a name, but keeping both is redundant
> and confusing, and `which slpy` may still resolve to the old dev symlink instead of the
> plugin's. After removing both old bits, install the plugin per step 3.

## Troubleshooting

| Symptom | Cause & fix |
|---|---|
| **MCP shows "not authenticated" / 401** | Credentials missing or wrong, or set in a different shell than the one running Claude Code. Re-check step 2 and restart Claude Code. |
| **MCP shows `! Needs authentication`** | No `Authorization` header reached the server, so Claude Code followed the server's OAuth challenge instead. On a pod that fronts the SnapLogic authorization server this is a **working sign-in path, not an error** — finish it with `/mcp`, or see [Optional: use SSO (OAuth) for the MCP server](#optional-use-sso-oauth-for-the-mcp-server). If you meant to use Basic, your credentials aren't reaching the helper: run it by hand in the same shell — macOS/Linux/Git-Bash: `python3 ~/.claude/plugins/cache/snapcode/*/*/bin/mcp_headers.py` · Windows PowerShell: `python (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\snapcode\*\*in\mcp_headers.py").FullName`. If it prints `{"Authorization": "Basic ..."}` your creds are read; if it prints `{}`, then `SNAPLOGIC_API_USER`/`SNAPLOGIC_API_PASS` aren't set in this shell — or `SNAPLOGIC_AUTH_MODE=oauth` is. |
| **Installer unreachable / org lookup fails / "credentials missing"** | Check the variable **name** is spelled exactly `SNAPLOGIC_ORG_NAME` — a misspelled name is silently ignored, so the org can't resolve and the slpy install fails. Fix the name, open a new terminal, restart. |
| **`CERTIFICATE_VERIFY_FAILED` / TLS certificate error during install** | Your Python has no usable CA trust store — common on **python.org macOS builds** where the bundled *Install Certificates.command* was never run (or a corporate proxy presents a custom root CA your Python can't see). The plugin now auto-recovers when `truststore`/`certifi` are importable; if it still fails, fix your Python's trust store: run `"/Applications/Python 3.x/Install Certificates.command"` (python.org build), **or** add `export SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())')"` to your shell profile — then open a new terminal and restart Claude Code. |
| **`slpy` not found / not installed** | The bootstrap installs it on the first session (and the launcher installs it on demand). If it's still missing, start a fresh session. If your pod is behind a proxy/firewall, the installer call must be able to reach the SLServer endpoint on your pod. |
| **`ENOENT: Bun could not find a file`** on `plugin marketplace add` / `install` | Usually a stale `CLAUDE_CONFIG_DIR` pointing at a directory that no longer exists. Check and clear it, then retry — macOS/Linux: `echo $CLAUDE_CONFIG_DIR` then `unset CLAUDE_CONFIG_DIR` · Windows PowerShell: `$env:CLAUDE_CONFIG_DIR` then `Remove-Item Env:\CLAUDE_CONFIG_DIR`. |
| **Used the old SnapCode repo before?** | The old distribution registered a user-scope MCP named `snaplogic`. The plugin adds its own (`snapcode:snaplogic`) — they don't share a name, but keeping both is redundant and confusing. Remove the old one: `claude mcp remove snaplogic` (run `claude mcp list` to see what's registered). |
