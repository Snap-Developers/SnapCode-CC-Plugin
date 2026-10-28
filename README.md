# SnapCode

A Claude Code **plugin marketplace** for SnapLogic SnapCode. Install the SnapCode plugin —
the `snaplogic` and `slpy` CLIs, the SnapLogic MCP server, and skills — with one command. No repo to clone, no container.

## Install

See **[docs/install-snapcode.md](docs/install-snapcode.md)** for the full guide. In short:

1. **Prerequisites:** Claude Code CLI **v2.1.195+** (check `claude --version`, update with `claude update`), Python 3.8+, and [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs the `slpy` CLI. See [docs/install-snapcode.md](docs/install-snapcode.md#1-prerequisites) for install commands.
2. **Install the plugin:**
   ```bash
   claude plugin marketplace add Snap-Developers/SnapCode-CC-Plugin
   claude plugin install snapcode@snapcode
   ```
3. **Sign in with your SnapLogic account** (not GitHub/AWS), one of the two:
   - **Username and password:** set these in your environment, then start `claude`.
     macOS / Linux — add to `~/.zshrc` / `~/.bashrc` to persist:
     ```bash
     export SNAPLOGIC_API_USER="you@yourcompany.com"
     export SNAPLOGIC_API_PASS="your-password"
     export SNAPLOGIC_BASE_URL="https://elastic.snaplogic.com"   # your SnapLogic control plane URL
     export SNAPLOGIC_ORG_NAME="your-org-name"
     ```
     Windows PowerShell — persist at the User level, then open a new terminal:
     ```powershell
     [Environment]::SetEnvironmentVariable('SNAPLOGIC_API_USER', 'you@yourcompany.com', 'User')
     [Environment]::SetEnvironmentVariable('SNAPLOGIC_API_PASS', 'your-password', 'User')
     [Environment]::SetEnvironmentVariable('SNAPLOGIC_BASE_URL', 'https://elastic.snaplogic.com', 'User')
     [Environment]::SetEnvironmentVariable('SNAPLOGIC_ORG_NAME', 'your-org-name', 'User')
     ```
   - **SSO:** set only `SNAPLOGIC_BASE_URL` and start `claude` once. It downloads the
     `snaplogic` CLI and shows the sign-in command, `! snaplogic auth login`, to send in the
     Claude Code session (add `--org <name>` if you have more than one organization).
     Then run `/mcp` to reconnect, and start `claude` again. See
     [docs/install-snapcode.md](docs/install-snapcode.md#3b-sso-browser-sign-in).

The plugin sets up the `snaplogic` and `slpy` CLIs, connects to the SnapLogic MCP server with
your password or your browser sign-in, and loads the skills. On first launch (and after each
plugin update) you'll see a **welcome message**; the first setup takes ~5–20s. Every session
then shows a **checklist**, one line per part marked `[ok]` or `[x]`, and what to do about anything
missing. Verify everything is wired up:

- **MCP:** `/mcp` — `snapcode:snaplogic` should show *connected*
- **Skills:** `/help` (or `/skills`) — `snaplogic-slpy-gen`, `snaplogic-deploy`, `agent-pipelines` and `mcp-server-pipelines` appear
- **slpy CLI:** `! slpy eval-expr -e '1 + 2'` — prints `3`

## What's in here

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace catalog |
| `plugin/` | The `snapcode` plugin (skills, SnapLogic MCP config, bootstrap) |
| `docs/` | One file per SnapCode doc page (`snapcode.md`, `install-snapcode.md`, `use-snapcode.md`, `troubleshoot-snapcode.md`) |

