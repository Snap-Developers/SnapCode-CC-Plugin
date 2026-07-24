# SnapCode — Setup

Install SnapCode as a single Claude Code plugin. No repo to clone, no container,
no GitHub or AWS account.

## 1. Prerequisites

Install these on your machine first:

| Tool | Why | Check |
|---|---|---|
| **Claude Code CLI** | Runs the plugin | `claude --version` |
| **Python 3.8+** | Runs the plugin's bootstrap + auth helper | `python3 --version` (macOS) / `python --version` (Windows) |
| **Node.js 18+** | Required by Claude Code, and by the Script snap in slpy | `node --version` |
| **uv** | Installs the slpy CLI (the plugin auto-installs it if missing) | `uv --version` |

> macOS uses `python3`; Windows uses `python`. The plugin handles both.

## 2. Set your SnapLogic credentials (in your environment)

SnapCode authenticates to the SnapLogic cloud with **your existing SnapLogic
credentials** — set them in your own shell environment. These are SnapLogic platform
credentials, **not** GitHub or AWS.

Set your SnapLogic credentials, pod URL, and org. **Most users should use
`SNAPLOGIC_ORG_NAME`** (just your org's name) — the plugin resolves the ID for you.

```bash
# macOS / Linux (add to ~/.zshrc or ~/.bashrc to persist)
export SNAPLOGIC_API_USER="you@yourcompany.com"
export SNAPLOGIC_API_PASS="your-password"
export SNAPLOGIC_BASE_URL="https://your-pod.snaplogic.com"
export SNAPLOGIC_ORG_NAME="your-org-name"        # e.g. "mycompany" — the org you work in
# Advanced: skip the lookup by giving the exact ID instead (takes priority if both set):
# export SNAPLOGIC_ORG_ID="your-24-char-org-id"
```
```powershell
# Windows PowerShell (use [Environment]::SetEnvironmentVariable to persist)
$env:SNAPLOGIC_API_USER = "you@yourcompany.com"
$env:SNAPLOGIC_API_PASS = "your-password"
$env:SNAPLOGIC_BASE_URL = "https://your-pod.snaplogic.com"
$env:SNAPLOGIC_ORG_NAME  = "your-org-name"
# Advanced: $env:SNAPLOGIC_ORG_ID = "your-24-char-org-id"
```

| Variable | What it is |
|---|---|
| `SNAPLOGIC_API_USER` / `_PASS` | Your SnapLogic platform login (email + password). **Not** GitHub/AWS. |
| `SNAPLOGIC_BASE_URL` | Your pod URL — the same host you use for the SnapLogic UI / MCP endpoint. |
| `SNAPLOGIC_ORG_NAME` | **Recommended.** Your org name (e.g. `mycompany`) — the name you see in the SnapLogic UI. The plugin resolves the ID automatically. |
| `SNAPLOGIC_ORG_ID` | Advanced/optional. The exact 24-char hex org ID. Only visible in Manager Settings to org admins, so most users should use `SNAPLOGIC_ORG_NAME` instead. |

> Set these **before** starting Claude Code, in the same shell. `SNAPLOGIC_API_USER/PASS`
> also authenticate the cloud MCP. If you change any, restart Claude Code.

## 3. Install the plugin

```bash
claude plugin marketplace add Snap-Developers/SnapCode-CC-Plugin
claude plugin install snapcode@snapcode
```

### First run — initialize once

The **first** Claude Code session after installing sets things up (installs the auth
helper and the `slpy` CLI). On that first session the cloud MCP may show as not
connected, because setup runs as the session starts. **Just start a session once to
initialize, then restart it (or run a new session).** From then on everything is ready
immediately — this one-time step is only needed right after install.

```bash
# in your repo/working dir, with credentials set (step 2):
claude          # start once to initialize, then exit
claude          # subsequent sessions: cloud MCP connected, slpy ready
```

After the first init, on every session the plugin:
- loads the SnapCode skills,
- connects to the SnapLogic cloud MCP using your credentials from step 2,
- has the `slpy` CLI ready.

### Updating

The plugin is a snapshot cloned locally — it does **not** auto-update. To pull the
latest (new skills, fixes):

```bash
claude plugin marketplace update snapcode     # fetch the latest from the repo
claude plugin update snapcode@snapcode         # apply it
```

> The `slpy` CLI is separate: the plugin refreshes it on its own (a daily check against
> the private index), so you don't need to update it by hand.

## 4. Verify

```bash
claude mcp list          # the "snapcode:snaplogic" MCP server should show Connected
```

In a Claude Code session:
```
! which slpy             # should point inside the snapcode plugin cache
! slpy translate --help  # the CLI runs
```
Then ask Claude to list snaps or generate a pipeline — it should use the cloud MCP
tools and the `slpy` CLI.

## Troubleshooting

- **Already used the old SnapCode repo? Remove the old `snaplogic` MCP first.** If you
  previously cloned the SnapCode repo, you likely have a `snaplogic` MCP server registered
  globally. It **conflicts** with the plugin's MCP (same name). Remove it before/after
  installing: `claude mcp remove snaplogic` (check `claude mcp list` for where it's declared).
- **`ENOENT: Bun could not find a file`** on `plugin marketplace add` / `install` — usually
  a stale `CLAUDE_CONFIG_DIR` pointing at a directory that no longer exists. Run
  `echo $CLAUDE_CONFIG_DIR`; if it's set to a missing path, `unset CLAUDE_CONFIG_DIR` (or
  point it at a real directory) and retry.
- **MCP shows "not authenticated" / 401** — credentials missing or wrong, or set in a
  different shell than the one running Claude Code. Re-check step 2 and restart.
- **MCP shows a 404 / OAuth error** — usually means no `Authorization` header reached
  the server; confirm your credentials are exported in the current environment.
- **Windows: MCP never connects, and `~/.claude/snapcode/` doesn't exist** — the
  `SessionStart` hook runs the bootstrap that installs the MCP auth helper. It tries
  `python3` first (macOS) and falls back to `python` (Windows). If you're on a very old
  plugin version the hook only tried `python3` — on Windows that hits the Microsoft Store
  alias stub ("Python was not found"), so the hook failed silently and the auth helper was
  never installed. Update the plugin (`claude plugin update snapcode@snapcode`) and restart.
- **`slpy` not found / not installed** — the bootstrap installs it on the first session;
  start a session once to initialize, then restart. If your pod is behind a proxy/firewall,
  the installer call must be able to reach the SLServer endpoint on your pod.
