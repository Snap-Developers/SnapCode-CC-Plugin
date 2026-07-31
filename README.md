# SnapCode

A Claude Code **plugin marketplace** for SnapLogic SnapCode. Install the SnapCode plugin —
skills, cloud MCP, and the slpy CLI — with one command. No repo to clone, no container.

## Install

See **[docs/setup.md](docs/setup.md)** for the full guide. In short:

1. **Prerequisites:** Claude Code CLI + Python 3.8+.
2. **Set your SnapLogic credentials + org in your environment** (not GitHub/AWS):
   ```bash
   export SNAPLOGIC_API_USER="you@yourcompany.com"
   export SNAPLOGIC_API_PASS="your-password"
   export SNAPLOGIC_BASE_URL="https://your-pod.snaplogic.com"
   export SNAPLOGIC_ORG_NAME="your-org-name"   # or SNAPLOGIC_ORG_ID="<24-char hex>"
   ```
3. **Install the plugin:**
   ```bash
   claude plugin marketplace add Snap-Developers/SnapCode-CC-Plugin
   claude plugin install snapcode@snapcode
   ```

Then start Claude Code — the plugin loads the skills, connects to the cloud MCP using
your credentials, and installs the `slpy` CLI on demand. On first launch you'll see a
**welcome message** once setup finishes (the `slpy` install runs in the background, ~5–20s).
Verify everything is wired up:

- **MCP:** `/mcp` — `snapcode:snaplogic` should show *connected*
- **Skills:** `/help` (or `/skills`) — the `snaplogic-slpy-gen` and `snaplogic-deploy` skills appear
- **slpy CLI:** `! slpy eval-expr -e '1 + 2'` — prints `3`

## What's in here

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace catalog |
| `plugin/` | The `snapcode` plugin (skills, cloud-MCP config, slpy bootstrap) |

