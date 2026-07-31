# SnapCode — Setup

Install SnapCode as a single Claude Code plugin. No repo to clone, no container,
no GitHub or AWS account.

## 1. Prerequisites

Install these on your machine first:

| Tool | Why | Check |
|---|---|---|
| **Claude Code CLI** | Runs the plugin | `claude --version` |
| **Python 3.8+** | Runs the plugin's bootstrap + auth helper | `python3 --version` (macOS) / `python --version` (Windows) |

> **macOS uses `python3`; Windows uses `python`** (on Windows `python3` is often a Microsoft
> Store stub that isn't a real interpreter). The plugin discovers whichever one works, so
> either is fine as long as one of them runs Python 3.

## 2. Set your SnapLogic credentials (in your environment)

SnapCode authenticates to the SnapLogic cloud with **your existing SnapLogic
credentials** — set them in your own shell environment.

Set your SnapLogic credentials, pod URL, and org.

**macOS / Linux** — add these lines to your shell profile (`~/.zshrc` on macOS, or
`~/.bashrc` on most Linux) so they **persist** across terminals, instead of a one-time
`export` that's lost when you close the window:

```bash
# Append to ~/.zshrc (macOS) or ~/.bashrc (Linux).
# Single quotes keep the values literal — a $, !, \ or backtick in your password
# won't be expanded by the shell. (If the password itself contains a single quote,
# close-escape-reopen: 'pa'\''ss' for pa'ss.)
export SNAPLOGIC_API_USER='you@yourcompany.com'
export SNAPLOGIC_API_PASS='your-password'
export SNAPLOGIC_BASE_URL='https://your-pod.snaplogic.com'
export SNAPLOGIC_ORG_NAME='your-org-name'
# Advanced: skip the lookup by giving the exact ID instead (takes priority if both set):
# export SNAPLOGIC_ORG_ID='your-24-char-org-id'
```
After saving, run `source ~/.zshrc` (or open a new terminal) so the values load — then
start Claude Code from that shell. Child processes inherit the environment at launch, so
restart Claude Code / your editor if it was already open.
```powershell
# Windows PowerShell — session-only (lost when you close the window):
# Single quotes keep the values literal — a $ or backtick in your password won't be
# treated as a PowerShell variable/escape. (If the password contains a single quote,
# double it: 'pa''ss' for pa'ss.)
$env:SNAPLOGIC_API_USER = 'you@yourcompany.com'
$env:SNAPLOGIC_API_PASS = 'your-password'
$env:SNAPLOGIC_BASE_URL = 'https://your-pod.snaplogic.com'
$env:SNAPLOGIC_ORG_NAME  = 'your-org-name'
# Advanced: $env:SNAPLOGIC_ORG_ID = 'your-24-char-org-id'
```
To **persist** on Windows, set them at the User level instead (single-quoted values stay
literal, so a `$` or backtick in your password isn't treated as a PowerShell variable/escape;
if the password contains a single quote, double it: `'pa''ss'`):
```powershell
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', 'you@yourcompany.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_PASS', 'your-password', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_BASE_URL', 'https://your-pod.snaplogic.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_ORG_NAME', 'your-org-name', 'User')
```
> Windows has no `source` equivalent: after `SetEnvironmentVariable`, the **current**
> window won't see the values — **open a new terminal** (and restart Claude Code / your
> editor, since child processes inherit the environment at launch). Verify with
> `[Environment]::GetEnvironmentVariable("SNAPLOGIC_ORG_NAME", "User")`.

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

> **Install scope.** By default `claude plugin install` enables SnapCode for **you**
> (user scope, `~/.claude/settings.json`). To scope it to a **single project** instead —
> so everyone who opens that repo gets SnapCode automatically — add `--scope project`:
> ```bash
> claude plugin install snapcode@snapcode --scope project
> ```
> This writes to the repo's `.claude/settings.json` (`extraKnownMarketplaces` +
> `enabledPlugins`). Commit that file and teammates get the plugin on their next session —
> no per-person install. Each person still sets their own `SNAPLOGIC_*` credentials (step 2).

### First run

Just start Claude Code in a directory where your credentials (step 2) are set:

```bash
# in your repo/working dir, with credentials set (step 2):
claude
```

On every session the plugin:
- loads the SnapCode skills,
- connects to the SnapLogic cloud MCP using your credentials from step 2,
- has the `slpy` CLI ready.

The cloud MCP authenticates with the auth helper that ships inside the plugin (no
install step, so it's ready on the **first** session). The `slpy` CLI is installed on
the first session by the SessionStart bootstrap; if you happen to run `slpy` before that
finishes, the launcher installs it on demand. If the MCP shows as not connected, see
Troubleshooting below (usually a credential or variable-name issue).

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
! slpy --help  # the CLI runs
```
Then ask Claude to list snaps or generate a pipeline — it should use the cloud MCP
tools and the `slpy` CLI.

## 5. Uninstall

```bash
claude plugin uninstall snapcode@snapcode
claude plugin marketplace remove snapcode
```

Those two commands remove the plugin and the marketplace entry. To also clear the bits
the plugin wrote outside its own directory (safe to delete — regenerated on reinstall):

```bash
rm -rf ~/.claude/plugins/cache/snapcode         # installed slpy (large)
```

If you set the `SNAPLOGIC_*` env vars in your shell profile (step 2) and no longer want
them, remove those lines from `~/.zshrc` / `~/.bashrc` too.

## Migrating from the old install (clone + Docker)

If you previously used the old SnapCode distribution (cloned the repo, ran the Docker
image, installed slpy/MCP globally), remove those first — they **conflict** with the
plugin:

```bash
claude mcp remove snaplogic     # old user-scope MCP clashes with the plugin's (same name)
rm ~/.local/bin/slpy            # old slpy symlink shadows the plugin's on PATH
```

Symptoms if you skip this: the plugin's `snapcode:snaplogic` MCP shows **failed** (the old
`snaplogic` MCP wins the name), and `which slpy` still points at the old dev symlink instead
of the plugin's. After removing both, install the plugin per step 3.

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
- **MCP shows a 404 / OAuth error** — means no `Authorization` header reached the server,
  so it fell back to OAuth discovery (which 404s on this endpoint). The header comes from
  the auth helper (`bin/mcp_headers.py`), run via the `.mcp.json` `headersHelper`. Confirm
  your credentials are exported in the current environment. To check directly, run the
  helper by hand in the same shell — if it prints `{"Authorization": "Basic ..."}` your
  creds are being read; if it prints just `{}`, `SNAPLOGIC_API_USER`/`SNAPLOGIC_API_PASS`
  aren't set in this shell. The helper lives under the installed plugin:

  ```bash
  # macOS / Linux / Git-Bash (use python on Windows):
  python3 ~/.claude/plugins/cache/snapcode/*/*/bin/mcp_headers.py
  ```
- **Installer unreachable / org lookup fails / "credentials missing"** — first check the
  variable **names** are spelled exactly `SNAPLOGIC_ORG_NAME` (or `SNAPLOGIC_ORG_ID`). A
  misspelled name is silently ignored, so the bootstrap can't resolve your org and the slpy
  installer endpoint call fails. Fix the name, open a new terminal, restart.
- **`slpy` not found / not installed** — the bootstrap installs it on the first session
  (and the launcher installs it on demand if you run `slpy` before that finishes). If it
  still isn't there, start a fresh session. If your pod is behind a proxy/firewall, the
  installer call must be able to reach the SLServer endpoint on your pod.
