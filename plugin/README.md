# snapcode plugin

**Single-command install:** install one Claude Code plugin → on session start it fetches
and installs the `slpy` CLI (no separate step) → skills + cloud MCP are wired up.
Cross-platform (macOS + Windows). Users need no GitHub or AWS account.

## What's inside

| Path | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `skills/` | `snaplogic-slpy-gen`, `snaplogic-deploy` (synced from the SnapCode repo) |
| `.mcp.json` | Cloud MCP registration (`snaplogic`, HTTP) — no local MCP, no container |
| `hooks/hooks.json` | `SessionStart` hook (needs a `matcher` to fire) that runs the bootstrap |
| `bin/bootstrap.py` | Ensures `uv`, fetches the installer URL, installs slpy into the persistent data dir |
| `bin/mcp_headers.py` | MCP auth helper — emits the `Authorization` header from env credentials |
| `bin/slpy`, `bin/slpy.cmd` | `slpy` launcher on PATH → forwards to the installed slpy |

## How slpy is installed (bootstrap)

On session start the `SessionStart` hook runs `bootstrap.py`, which:
1. copies the MCP auth helper to `~/.claude/snapcode/mcp_headers.py` (a fixed path the
   `.mcp.json` `headersHelper` can reach),
2. calls the SLServer installer endpoint with the user's SnapLogic credentials (Basic auth):
   `GET {SNAPLOGIC_BASE_URL}/api/1/rest/slserver/snapcode/{org_id}/fetch_installer`
   → returns `{"response_map": [{"index_url": "<token-embedded private index URL>"}]}`,
3. runs `uv tool install slpy` with that index URL passed via `UV_DEFAULT_INDEX` (token never
   on the command line), landing slpy in `${CLAUDE_PLUGIN_DATA}/bin/`.

To keep it fast, bootstrap checks the index at most once per TTL window (default 24h); between
checks an already-installed slpy is reused with no network call.

`org_id` is resolved from `SNAPCODE_ORG_ID` (direct) or `SNAPCODE_ORG_NAME` (looked up via
`/api/1/rest/public/users/{email}`). Requests send an identifying `User-Agent` so pods behind
Cloudflare bot protection don't reject them (1010).

## Try it locally

```bash
# set SNAPLOGIC_API_USER / _PASS / _BASE_URL and SNAPCODE_ORG_ID (or _NAME) first
claude --plugin-dir ./plugin
```

See [../docs/setup.md](../docs/setup.md) for the full setup guide.

## Status

End-to-end verified on canary (hook fires → installer endpoint → slpy installed, zero manual
steps). Pending: the installer endpoint's deployment to prod (currently canary only).
