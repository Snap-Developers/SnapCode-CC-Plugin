# SnapCode

A Claude Code **plugin marketplace** for SnapLogic SnapCode. Install the SnapCode plugin —
skills, cloud MCP, and the slpy CLI — with one command. No repo to clone, no container.

## Install

```bash
# add this marketplace, then install the plugin
claude plugin marketplace add Snap-Developers/SnapCode
claude plugin install snapcode@snapcode
```

That's it — the plugin brings the SnapCode skills, wires up the cloud MCP server, and
(in production) installs the `slpy` CLI on demand.

## What's in here

| Path | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace catalog |
| `plugin/` | The `snapcode` plugin (skills, cloud-MCP config, slpy bootstrap) |

## Notes

- This repo is **public on purpose** and contains **no private code**. The skills, MCP config,
  and bootstrap scripts are not sensitive; the private `slpy` source is **never** shipped here.
- In production, `slpy` is installed from a private index (CodeArtifact) authorized by the
  user's SnapLogic identity via a token broker — so end users need no GitHub or AWS account.
- Status: POC. The token-broker piece is still in progress; until then the plugin loads the
  skills + cloud MCP, and slpy auto-install is wired but pending the private-index path.
