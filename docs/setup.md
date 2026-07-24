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

Set your SnapLogic credentials, pod URL, and org identifier.

```bash
# macOS / Linux (add to ~/.zshrc or ~/.bashrc to persist)
export SNAPLOGIC_API_USER="you@yourcompany.com"
export SNAPLOGIC_API_PASS="your-password"
export SNAPLOGIC_BASE_URL="https://your-pod.snaplogic.com"

# Identify your org — use one of these two (ID takes priority if both are set):
export SNAPCODE_ORG_ID="your-24-char-org-id"   # exact hex ID — found in Manager > Settings
# or:
export SNAPCODE_ORG_NAME="your-org-name"        # e.g. "mycompany" — bootstrap resolves the ID automatically
```
```powershell
# Windows PowerShell (use [Environment]::SetEnvironmentVariable to persist)
$env:SNAPLOGIC_API_USER = "you@yourcompany.com"
$env:SNAPLOGIC_API_PASS = "your-password"
$env:SNAPLOGIC_BASE_URL = "https://your-pod.snaplogic.com"
$env:SNAPCODE_ORG_ID = "your-24-char-org-id"    # or use SNAPCODE_ORG_NAME below
$env:SNAPCODE_ORG_NAME = "your-org-name"
```

| Variable | What it is |
|---|---|
| `SNAPLOGIC_API_USER` / `_PASS` | Your SnapLogic platform login (email + password). **Not** GitHub/AWS. |
| `SNAPLOGIC_BASE_URL` | Your pod URL — the same host you use for the SnapLogic UI / MCP endpoint. |
| `SNAPCODE_ORG_ID` | Your org's 24-char hex ID. Find it in Manager → your org → Settings → "Organization Id". |
| `SNAPCODE_ORG_NAME` | Your org name (e.g. `mycompany`). If set without `SNAPCODE_ORG_ID`, bootstrap looks up the ID automatically. |

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

## 4. Verify

```bash
claude mcp list          # the "snapcode" / snaplogic MCP server should show Connected
```

In a Claude Code session, ask it to list snaps or generate a pipeline — it should use
the cloud MCP tools and the `slpy` CLI.

## Troubleshooting

- **MCP shows "not authenticated" / 401** — credentials missing or wrong, or set in a
  different shell than the one running Claude Code. Re-check step 2 and restart.
- **MCP shows a 404 / OAuth error** — usually means no `Authorization` header reached
  the server; confirm your credentials are exported in the current environment.
- **`slpy` not found** — the bootstrap installs it on first session; if `uv` was just
  installed you may need to restart the session.
