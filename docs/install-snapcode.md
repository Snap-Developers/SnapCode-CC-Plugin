# Install SnapCode

Install SnapCode as a single Claude Code plugin. No repo to clone, no container,
no GitHub or AWS account.

## 1. Prerequisites

Install these on your machine first:

| Tool | Why | Check |
|---|---|---|
| **Claude Code CLI** (v2.1.195+) | Runs the plugin | `claude --version` |
| **Python 3.8+** | Runs the plugin's bootstrap + auth helper | `python3 --version` (macOS) / `python --version` (Windows) |
| **uv** | Installs the `slpy` CLI. See [Installing uv](https://docs.astral.sh/uv/getting-started/installation/) | `uv --version` |

> **macOS uses `python3`; Windows uses `python`** (on Windows `python3` is often a Microsoft
> Store stub that isn't a real interpreter). The plugin discovers whichever one works, so
> either is fine as long as one of them runs Python 3.

### Install or update the Claude Code CLI

Don't have it yet? Install it —

**macOS / Linux / WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
**Windows PowerShell:**
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

## 2. Install the plugin

Run these two commands:

```bash
claude plugin marketplace add Snap-Developers/SnapCode-CC-Plugin
claude plugin install snapcode@snapcode
```

This only installs it. The plugin sets itself up the first time you start Claude Code,
in step 3.

## 3. Sign in: pick one

SnapCode signs in to SnapLogic with **your existing SnapLogic account**, **not** GitHub or
AWS. There are two ways; use one or the other, not both:

| You sign in to the SnapLogic UI with | Follow |
|---|---|
| A username and password | [3a. Username and password](#3a-username-and-password) |
| Your company's single sign-on (SSO) | [3b. SSO (browser sign-in)](#3b-sso-browser-sign-in) |

### 3a. Username and password

**1. Set four variables** in your environment:

| Variable | What it is |
|---|---|
| `SNAPLOGIC_API_USER` / `SNAPLOGIC_API_PASS` | Your SnapLogic platform login (email + password). Also authenticates the SnapLogic MCP server. |
| `SNAPLOGIC_BASE_URL` | Your control plane URL — the address in your browser when you use SnapLogic, one of `https://elastic.snaplogic.com` (US), `https://elastic2.snaplogic.com` (US-East) or `https://emea.snaplogic.com` (EU), written exactly as `https://<host>`: lowercase, with no trailing `/`. |
| `SNAPLOGIC_ORG_NAME` | Your SnapLogic organization name — usually your company/team name. Required with a username and password, to install the `slpy` CLI. If you're not sure of the exact name, ask your SnapLogic admin. |

> Set these **before** starting Claude Code. If you change any later, restart Claude Code.

**macOS / Linux:** add these lines to your shell profile — `~/.zshrc` on macOS, or `~/.bashrc`
on most Linux — so they **persist** across terminals, instead of a one-time `export` that's
lost when you close the window:

```bash
export SNAPLOGIC_API_USER='you@yourcompany.com'
export SNAPLOGIC_API_PASS='your-password'
export SNAPLOGIC_BASE_URL='https://elastic.snaplogic.com'
export SNAPLOGIC_ORG_NAME='your-org-name'
```

Single quotes keep the values literal, so a `$`, `!`, `\`, or backtick in your password
won't be expanded by the shell. (If the password itself contains a single quote, use
`'pa'\''ss'` for `pa'ss`.)

After saving, run `source ~/.zshrc` (or open a new terminal) so the values load — then
start Claude Code from that shell. Child processes inherit the environment at launch, so
restart Claude Code / your editor if it was already open.

**Windows (PowerShell):** set them at the User level so they **persist** and new terminals see
them:

```powershell
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', 'you@yourcompany.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_PASS', 'your-password', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_BASE_URL', 'https://elastic.snaplogic.com', 'User')
[Environment]::SetEnvironmentVariable('SNAPLOGIC_ORG_NAME', 'your-org-name', 'User')
```

Single-quoted values stay literal, so a `$` or backtick in your password isn't treated as
a PowerShell variable/escape (if the password contains a single quote, double it:
`'pa''ss'`).

Windows has no `source` equivalent: after `SetEnvironmentVariable`, the **current** window
won't see the values — **open a new terminal** (and restart Claude Code / your editor,
since child processes inherit the environment at launch). Verify in the new terminal with
`echo $env:SNAPLOGIC_BASE_URL`.

**2. Start Claude Code** from your working directory:

```bash
claude
```

The first session downloads the `snaplogic` CLI and installs `slpy` (give it ~5–20s), then
shows the welcome and the checklist, every line `[ok]`.

### 3b. SSO (browser sign-in)

**1. Set only `SNAPLOGIC_BASE_URL`**, your control plane URL (the address in your browser when you use
SnapLogic: `https://elastic.snaplogic.com`, `https://elastic2.snaplogic.com` or
`https://emea.snaplogic.com`), written exactly as `https://<host>`: lowercase, with no trailing `/`. Leave
`SNAPLOGIC_API_USER` and `SNAPLOGIC_API_PASS` unset: if you set them for 3a before, remove
**both**, because sign-in refuses while either is set. You pick the organization when you sign
in, or set `SNAPLOGIC_ORG_NAME` to skip the question.

**macOS / Linux**, in `~/.zshrc` or `~/.bashrc` (then `source` it or open a new terminal):
```bash
export SNAPLOGIC_BASE_URL='https://elastic.snaplogic.com'
```
**Windows PowerShell** (then open a new terminal):
```powershell
[Environment]::SetEnvironmentVariable('SNAPLOGIC_BASE_URL', 'https://elastic.snaplogic.com', 'User')
```

**2. Start Claude Code once:**

```bash
claude
```

The first session downloads the `snaplogic` CLI. You are not signed in yet, so the checklist
shows `[x]` for Sign-in, slpy and SnapLogic MCP, and underneath it the command for step 3.
This is expected.

**3. Sign in.** Send this command in the Claude Code session:

```
! snaplogic auth login
```

It signs in to the control plane `SNAPLOGIC_BASE_URL` names (step 1). If you belong to more
than one organization, add `--org <name>`. The browser page says **Authorize SnapLogic CLI**:
that is the plugin's CLI, approve it. Then run `/mcp` and reconnect snaplogic.

**4. Start a new Claude Code session.** The plugin installs `slpy`, and every line of the
checklist shows `[ok]`. (In a session that is still open, running `slpy` finishes the setup too.)

The sign-in renews itself while you use it. You sign in again when it has gone unused for a
while, reaches its maximum lifetime, or after you sign out of SnapLogic;
`! snaplogic auth status` shows both limits. Running `! snaplogic auth login` while still
signed in says so and doesn't open the browser; run `! snaplogic auth logout` first to sign in
as someone else.

You can be signed in to one control plane at a time. To switch, run `! snaplogic auth logout`,
exit Claude Code, point `SNAPLOGIC_BASE_URL` at the new one (step 1), start Claude Code again
and sign in as in step 3.

### Every session

On every session the plugin loads the SnapCode skills, connects to the SnapLogic MCP server,
and has the `slpy` CLI ready.

The SnapLogic MCP server uses the password from 3a when it is set, otherwise your browser
sign-in, the same as the `snaplogic` CLI. With several Claude Code sessions on the same
SnapLogic address, it follows the one started last. On the very first session it may not be
connected yet: run `/mcp` and reconnect, or start a new session. If it still shows as not
connected, see [Troubleshoot SnapCode](troubleshoot-snapcode.md) (usually a credential or variable-name issue).

### Updating

The plugin is a snapshot cloned locally, and auto-update is **off** by default. New plugin
versions ship with SnapLogic's monthly platform release. Every session start checks for a newer
version: when one is out, the first thing the session shows is how to update.

**Turn on auto-update** using one of the following ways:

- In Claude Code, run `/plugin`, open **Marketplaces**, select **snapcode**, then **Enable auto-update**.
- Or add `"autoUpdate": true` to the `snapcode` entry under `extraKnownMarketplaces` in
  `~/.claude/settings.json`:

  ```json
  {
    "extraKnownMarketplaces": {
      "snapcode": {
        "source": { "source": "github", "repo": "Snap-Developers/SnapCode-CC-Plugin" },
        "autoUpdate": true
      }
    }
  }
  ```

With auto-update on, Claude Code checks for a new version within 10 minutes of the first
message in each session. When it installs one, it shows `Plugin updated: snapcode · Run
/reload-plugins to apply`: run `/reload-plugins` to use it now, or it loads on your next launch.

**To update manually**, run these two commands (the first fetches the latest from the repo, the
second applies it), then run `/reload-plugins`:

```bash
claude plugin marketplace update snapcode
claude plugin update snapcode@snapcode
```

> The `slpy` and `snaplogic` CLIs are separate and update on their own: the plugin
> refreshes `slpy` daily, and `snaplogic` updates itself when a newer version is out,
> so you don't need to update them by hand.

## 4. Verify

The checklist at the start of every session checks the CLIs, your sign-in, the SnapLogic MCP
configuration and the skills: every line should show `[ok]`. The one thing it cannot see is
whether the MCP server actually connected, which happens after the session starts, so run:

```
/mcp
```

Expected: `plugin:snapcode:snaplogic` shows **connected**. Then ask Claude to list snaps or
generate a pipeline.

### CLI usage identification

When SnapCode runs the `snaplogic` CLI, it sets `SNAPLOGIC_CLIENT=snapcode/<plugin version>` on
that call, and the CLI adds it to the request's `User-Agent` so SnapLogic can tell SnapCode's
usage apart. Nothing is written to your files, no personal data is sent, and running the CLI
outside Claude Code is not tagged.

To opt out on macOS / Linux, set it to an empty value before starting Claude Code
(`export SNAPLOGIC_CLIENT=`). On Windows an empty variable counts as unset, so set it to another
value such as `none`; requests then carry that value instead of `snapcode`.

## 5. Uninstall

If you signed in through the browser, sign out first, in Claude Code while the plugin is
still installed:

```
! snaplogic auth logout
```

Then remove the plugin and the marketplace entry:

```bash
claude plugin uninstall snapcode@snapcode
claude plugin marketplace remove snapcode
```

To also clear what the plugin wrote outside its own directory (safe to delete, regenerated
on reinstall; the data directory holds the installed `slpy` and `snaplogic`, which can be
large):

**macOS / Linux:**
```bash
rm -rf ~/.claude/plugins/cache/snapcode
rm -rf ~/.claude/plugins/data/snapcode-snapcode   # slpy and the snaplogic CLI
rm -rf ~/.claude/snapcode   # the auth helper's copy of your credentials
```
**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\cache\snapcode"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\data\snapcode-snapcode"   # slpy and the snaplogic CLI
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\snapcode"   # the auth helper's copy of your credentials
```

If you set the `SNAPLOGIC_*` env vars (step 3) and no longer want them:
- **macOS / Linux:** remove those `export` lines from `~/.zshrc` / `~/.bashrc`.
- **Windows PowerShell:** clear each User-level var, e.g.
  `[Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', $null, 'User')` (repeat per variable).

## Troubleshooting

See [Troubleshoot SnapCode](troubleshoot-snapcode.md) for help with downloading the CLI, sign-in,
`slpy` installation and MCP connection issues.
