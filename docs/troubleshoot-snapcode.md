# Troubleshoot SnapCode

Messages in quotes are what the session start or the command prints.

## Downloading the `snaplogic` CLI (first session)

| What you see | Cause | Fix |
|---|---|---|
| `[x]  snaplogic CLI — not available` and "could not set up the slpy CLI — `<address>` answered HTTP `<code>`. That is the download service, not your machine or network." | The CLI download service on your control plane returned an error. | Check that `SNAPLOGIC_BASE_URL` is your control plane URL ([step 3](install-snapcode.md#3-sign-in-pick-one)). If it is, start a new session later; if it persists, contact SnapLogic support with the HTTP code. |
| "could not set up the slpy CLI — the CLI could not be downloaded. Check network access to `<address>`." | The machine can't reach the download service (proxy, firewall, VPN, offline), or `SNAPLOGIC_BASE_URL` is mistyped. | Check the address in the message, allow HTTPS to it, then start a new session. |
| "… this is a TLS trust problem, NOT a credentials/URL problem …" or `CERTIFICATE_VERIFY_FAILED` | Your Python has no usable CA trust store: common on **python.org macOS builds** where the bundled *Install Certificates.command* was never run, or a corporate proxy presents a root CA your Python can't see. | The plugin recovers on its own when `truststore`/`certifi` are importable. Otherwise run `"/Applications/Python 3.x/Install Certificates.command"` (python.org build), **or** add `export SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())')"` to your shell profile, then open a new terminal and restart Claude Code. |
| "the `snaplogic` CLI was downloaded but will not run on this machine" | The downloaded build doesn't match the machine (OS or CPU architecture). | Contact SnapLogic support with your OS and architecture (`uname -sm`, or on Windows `echo $env:PROCESSOR_ARCHITECTURE`). |
| "the published `snaplogic` CLI is older than the plugin expects and cannot install slpy" | The published CLI predates the plugin. | Nothing to fix locally; it needs a newer CLI release. |

## Address and sign-in

| What you see | Cause | Fix |
|---|---|---|
| `[x]  Sign-in — no SnapLogic address: SNAPLOGIC_BASE_URL is not set` | No address configured. | Set `SNAPLOGIC_BASE_URL` ([step 3](install-snapcode.md#3-sign-in-pick-one)) and restart Claude Code. |
| "SNAPLOGIC_BASE_URL: "`<value>`" must be written as `https://<host>`" | The address has no `https://`, a trailing `/`, or capital letters. The CLI and the SnapLogic MCP server use it exactly as written. | Set it to the form the message shows, open a new terminal, restart Claude Code. |
| "… is not a SnapLogic address" | `SNAPLOGIC_BASE_URL` is not a SnapLogic control plane address; the message lists the domains allowed. | Set it to your control plane URL ([step 3](install-snapcode.md#3-sign-in-pick-one)). |
| "currently signed in to `<address>`, and only one pod can be signed in to at a time" | `snaplogic auth login` for one control plane while signed in to another. | Sign out of the old one first, then sign in: `! SNAPLOGIC_BASE_URL=https://<old host> snaplogic auth logout`, then `! snaplogic auth login`. |
| `` [x]  Sign-in — `snaplogic auth status`: not signed in to <host> ``, with `[x]  SnapLogic MCP — not signed in` | No password in the environment and no browser sign-in, or the sign-in expired (unused for a while, past its maximum lifetime, or you signed out of SnapLogic). | Sign in as the note under the checklist says ([3b, steps 3 and 4](install-snapcode.md#3b-sso-browser-sign-in)), then start a new session, or run `slpy` in the open one to finish setting up. |
| `` [x]  Sign-in — `snaplogic auth status` did not answer `` | The `snaplogic` CLI did not run, or gave an answer the plugin could not read. | Run `! snaplogic auth status` in Claude Code to see its error, then start a new session. |
| `snaplogic auth login` ends with "timed out waiting for the browser callback" | The browser part has 3 minutes. | Run `! snaplogic auth login` again and finish in the browser within 3 minutes, in a browser on the same machine (it returns to `127.0.0.1`). |
| Claude was asked to sign you in | Sign-in opens your browser and waits for you, so it is yours to run, not Claude's. | Type `! snaplogic auth login` at the prompt yourself ([3b, step 3](install-snapcode.md#3b-sso-browser-sign-in)). |
| The browser goes straight to **Authorize SnapLogic CLI** without a sign-in page | You are already signed in to SnapLogic in that browser. | Expected. Check the "signed in as" line; for another account, sign out of SnapLogic there or use a private window. |
| "Already signed in to `<address>` as `<user>`" | A valid sign-in exists. | Expected. To sign in again, run `! snaplogic auth logout` first. |
| "SNAPLOGIC_API_USER and SNAPLOGIC_API_PASS are for `<user>` on `<address>`, but a login for `<user>` on `<address>` is also saved" | You set a password **and** signed in through the browser, for a different control plane or user. The CLI stops rather than pick one. | Use one or the other: unset both `SNAPLOGIC_API_USER` and `SNAPLOGIC_API_PASS` to use the browser sign-in, or run `! snaplogic auth logout`, which with the password set deletes every saved sign-in. |
| "SNAPLOGIC_API_USER is set but SNAPLOGIC_API_PASS is not set" (or the reverse) | Only half of the password pair is set, often one left over from a password setup. | Set both to sign in with a password (3a), or unset the one that is set to use browser sign-in (3b). Open a new terminal, restart Claude Code. |
| "credentials file `<path>` is open to other users" | The file holding your browser sign-in can be read by other users of this machine. | `chmod 600 <path>` as the message says. |

## Installing slpy

| What you see | Cause | Fix |
|---|---|---|
| `[x]  slpy — not installed` with a sign-in note underneath | slpy is installed through your sign-in, and there is none yet. | Sign in (above). |
| "uv is not installed: install it from https://docs.astral.sh/uv/getting-started/installation/ and run this again" | uv, which installs slpy, is missing. | Install uv from that page, open a new terminal, start a new session. |
| "could not install the slpy CLI. The CLI reported: … Authentication required." | Your `SNAPLOGIC_API_PASS` was rejected. | Check it by signing in to the SnapLogic UI; fix it, open a new terminal, restart Claude Code. Repeated failures can lock the account. |
| "… no organization for this deployment: set SNAPLOGIC_ORG_NAME, or pass --org" | Username and password without `SNAPLOGIC_ORG_NAME`. | Set it, spelled exactly `SNAPLOGIC_ORG_NAME`: a misspelled variable name is silently ignored. Open a new terminal, restart Claude Code. |
| "… no organization recorded for this deployment: run `snaplogic auth login --org <name>` to record one, or pass --org" | Browser sign-in without a default organization. | `! snaplogic auth login --org <name>`: sets it without reopening the browser if you are signed in. |
| "SNAPLOGIC_ORG_NAME is "`<A>`" but the saved login's default organization is "`<B>`"" | `SNAPLOGIC_ORG_NAME` is left over from a password setup, and your browser sign-in recorded another organization. | Unset `SNAPLOGIC_ORG_NAME`, or run `! snaplogic auth login --org <A>` to make it the default. |
| `slpy` still missing after signing in | The installer endpoint on your control plane can't be reached (proxy/firewall). | The machine must reach your SnapLogic address. Start a new session. |

## After changing your password

| What you see | Cause | Fix |
|---|---|---|
| `Authentication required`, MCP 401s, or the account locks soon after a password change | Claude Code sessions opened before the change still use the old password. | Close sessions opened before the change and start new ones from a terminal with the new password. |

## SnapLogic MCP server

| Symptom | Cause & fix |
|---|---|
| **MCP shows "not authenticated" / 401** | If you sign in through the browser, the sign-in has expired or you are not signed in: run `! snaplogic auth login` in Claude Code (3b, step 3), then `/mcp` to reconnect. With a password: it is missing or wrong, or set in a different shell than the one running Claude Code. Re-check 3a and restart Claude Code. |
| **MCP shows a 404 / OAuth error** (for example "Protected resource … does not match") | Claude Code fell back to its own OAuth, which happens only when the plugin's auth helper (`bin/mcp_headers.py`) did not run or failed. Run it by hand in the same shell to check — **macOS/Linux/Git-Bash:** `python3 ~/.claude/plugins/cache/snapcode/*/*/bin/mcp_headers.py` · **Windows PowerShell:** `python (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\snapcode\*\*\bin\mcp_headers.py").FullName`. It should print `{"X-MCP-Tool-Profile": "snapcode", "Authorization": "..."}`: `Bearer` plus a token means your browser sign-in is used, `Basic` means your password, and `Bearer snapcode-not-signed-in` means neither was found (sign in, or set the 3a variables and restart Claude Code). The output contains your credential: don't paste it anywhere. |

## Other

| Symptom | Cause & fix |
|---|---|
| **`/mcp` shows no `plugin:snapcode:snaplogic`, or `/snaplogic` lists no SnapCode skills** | The plugin is not installed, or it is disabled. `claude plugin list` should include `snapcode@snapcode`. If it does not, install it ([step 2](install-snapcode.md#2-install-the-plugin)); if it is disabled, enable it under **Installed** in `/plugin`. Then run `/reload-plugins` in any open session. |
| **`ENOENT: Bun could not find a file`** on `plugin marketplace add` / `install` | Usually a stale `CLAUDE_CONFIG_DIR` pointing at a directory that no longer exists. Check and clear it, then retry — **macOS/Linux:** `echo $CLAUDE_CONFIG_DIR` then `unset CLAUDE_CONFIG_DIR` · **Windows PowerShell:** `$env:CLAUDE_CONFIG_DIR` then `Remove-Item Env:\CLAUDE_CONFIG_DIR`. |

## Pipeline validation and execution

| Symptom | Cause & fix |
|---|---|
| **Validation fails after deploy with a Snap or field error** | A Snap parameter is missing, has the wrong type, or references a field that does not exist. SnapCode fixes the `.py` and redeploys on its own, up to 5 times. If it still fails, tell SnapCode what the correct value should be, for example `Fix it: subtotal should be qty × unit_price`. |
| **The pipeline passes `slpy exec` locally but fails Platform validation or execution** (or the reverse) | The local engine and the SnapLogic Platform behave differently. Report it to the SnapCode team with the pipeline file and the exact error. |

## Checks when nothing above fits

- `! which slpy` should point inside `~/.claude/plugins/` (not an old `~/.local/bin/slpy`).
- `! slpy --help` should print the usage.
- `/snaplogic` should list `snaplogic-slpy-gen`, `snaplogic-deploy`, `agent-pipelines` and `mcp-server-pipelines`.
