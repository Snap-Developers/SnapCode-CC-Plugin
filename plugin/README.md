# snapcode plugin (POC)

Proves the **single-command install**: install one Claude Code plugin → on session start it
auto-installs the `slpy` CLI (no separate step) → skills + cloud MCP are wired up.
Cross-platform (macOS + Windows).

## What's inside

| Path | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `skills/` | `snaplogic-slpy-gen`, `snaplogic-deploy` |
| `.mcp.json` | Cloud MCP (SnapLabs HTTP endpoint) — no local MCP, no container |
| `hooks/hooks.json` | `SessionStart` hook (exec form → cross-platform, no shell) |
| `bin/bootstrap.py` | Idempotent installer: ensures `uv`, installs slpy into the persistent data dir |
| `vendor/slpy-*.whl` | **POC only** — local slpy wheel (later: private index) |

## Try it

```bash
# from the snapcode repo root
claude --plugin-dir ./plugin
```

On session start the hook runs `bootstrap.py`, which:
1. ensures `uv` is present (auto-installs if missing),
2. installs slpy from `vendor/*.whl` into `${CLAUDE_PLUGIN_DATA}` (persists across sessions),
3. is a no-op on later sessions unless the bundled wheel version changes.

slpy lands at `~/.claude/plugins/data/<id>/bin/slpy` (`slpy.exe` on Windows).

## POC vs. product

| | POC (now) | Product |
|---|---|---|
| slpy source | bundled wheel in `vendor/` | private index (CodeArtifact via broker, or self-hosted PyPI) |
| auth | none (local wheel) | one-time SnapLogic login (browser OAuth / SSO/MFA), token reused for MCP too |
| MCP | SnapLabs HTTP endpoint | production cloud MCP endpoint |

Swapping the local wheel for the private index is a one-line change in `bootstrap.py`
(`uv tool install slpy --index-url <…>` instead of the vendored `.whl`).
