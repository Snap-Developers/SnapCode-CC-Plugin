# SnapCode

A Claude Code **plugin marketplace** for SnapLogic SnapCode. Install the SnapCode plugin —
skills, cloud MCP, and the slpy CLI — with one command. No repo to clone, no container.

## Install

See **[docs/setup.md](docs/setup.md)** for the full guide. In short:

1. **Prerequisites:** Claude Code CLI, Python 3.8+, Node.js 18+ (uv is auto-installed if missing).
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
your credentials, and installs the `slpy` CLI on demand.

## What's in here

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace catalog |
| `plugin/` | The `snapcode` plugin (skills, cloud-MCP config, slpy bootstrap) |

## Notes

- This repo is **public on purpose** and contains **no private code**. The skills, MCP config,
  and bootstrap scripts are not sensitive; the private `slpy` source is **never** shipped here.
- `slpy` is installed from a private index (CodeArtifact) authorized by the user's SnapLogic
  identity: on session start the bootstrap calls the SLServer installer endpoint
  (`/api/1/rest/slserver/snapcode/{org_id}/fetch_installer`), which returns a short-lived,
  token-embedded index URL, then `uv` installs slpy from it — so end users need no GitHub or AWS.
- Status: end-to-end verified on canary (hook → installer endpoint → slpy installed). Pending:
  the installer endpoint's deployment to prod (currently canary only).
