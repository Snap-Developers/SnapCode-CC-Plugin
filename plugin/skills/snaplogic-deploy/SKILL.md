---
name: snaplogic-deploy
description: "Deploy, validate, and iteratively fix SnapLogic pipelines on the Control Plane. Covers the full loop: translate .py → .slp, upload supporting files, import to platform, validate, surface errors, fix source, repeat until validation passes."
tools: Read, Write, Bash, TodoWrite, mcp__snaplogic__import_pipeline, mcp__snaplogic__validate_pipeline, mcp__snaplogic__execute_pipeline, mcp__snaplogic__list_snaplexes, mcp__snaplogic__save_user_preferences, mcp__snaplogic__upload_sldb
---

# SnapLogic Deploy Skill

## 1. Overview

This skill owns the deploy→validate→fix loop for SnapLogic pipelines on the Control Plane. It picks up where `snaplogic-slpy-gen` leaves off: given a `.py` (SLPy) file, it translates, uploads supporting files, deploys to the platform, validates, surfaces all errors and schema details, and iterates until validation passes.

### When to Use This Skill

Invoke when the user wants to:
- Deploy a pipeline to the SnapLogic Control Plane
- Validate a pipeline already on the platform
- Fix a pipeline that fails validation
- Run the full generate→deploy→validate→fix loop end to end

---

## 2. SnapLogic Concepts & Terminology

Deploying correctly depends on getting SnapLogic's structure right. Read this before the workflow — most deploy failures come from confusing these terms (e.g. passing a project name where an org is expected).

### The hierarchy

```
Control Plane (SnapLogic-hosted)
  └── Org (tenant)                    e.g. "snaplogic", "ConnectFasterInc"
        ├── Project Space             e.g. "projects", a per-user space
        │     └── Project             e.g. "MyProject"  ← holds assets
        │           └── Assets: Pipeline, File, Account, Task, ...
        └── Snaplex                   org-level, shared across projects
```

Assets live at `{org}/{project_space}/{project}/{asset}`. `shared` is a special **Project** that sits directly under the org (so `{org}/shared/{asset}`).

### Terms

- **Control Plane** — the SnapLogic-hosted management layer (metadata, orchestration, scheduling, monitoring). The MCP server talks to it via `SNAPLOGIC_BASE_URL`. Distinct from the *execution plane* where data actually flows.
- **Org (Organization)** — the top-level tenant. Contains project spaces and Snaplexes. This is the **`org`** parameter (the org **name**, e.g. `snaplogic`) on nearly every MCP tool.
- **Project Space** — the grouping level directly under the org. **Contains Projects.**
- **Project** — the leaf container that actually holds assets (pipelines, files, accounts…). `shared` is a project directly under the org.
- **`project_path`** (MCP parameter) — the path to a project **within the org, WITHOUT the org name** — e.g. `projects/MyProject`, or just `shared`. The server prepends the org itself. When a user names "the **X** project", that's the `project_path`, **NOT the org** — never pass a project name as `org`.
- **Asset** — any addressable object in a project. Types: **Pipeline, Task (asset type `Job`), File, Account, Policy, Flows**. A pipeline is one asset.
- **Pipeline** — a data-integration flow (stored as SLP/JSON); the unit you import/validate/execute. **Snap** — one processing node *inside* a pipeline (read/transform/write step); not separately addressable.
- **Snaplex** — the execution engine (a cluster of JCC nodes) that runs pipelines. It is **org-level and shared, not under a project** — so `list_snaplexes` needs the **org**, not a project. Types: **Cloudplex** (SnapLogic-hosted) and **Groundplex** (customer-hosted, e.g. for local-file access).
- **`snaplex_path` / `runtime_path_id`** — the routing id of a Snaplex, format `<org_id>/rt/<location>/<environment>` (e.g. `snaplogic/rt/cloud/dev`). A Snaplex has both a browse `path` (a label) and a `runtime_path_id`; the MCP `snaplex_path` parameter wants the **`runtime_path_id`**. Discover both via `list_snaplexes`.
- **SLDB** — SnapLogic's built-in file store (referenced by `sldb:///` URIs). It's the storage layer behind project **Files**: a "File" asset is how SLDB-stored bytes appear in the project tree. `upload_sldb` / `download_sldb_file` operate on it via `org` + `project_path` + file name.
- **Account** — an asset holding connection credentials (DB, S3, …) used by snaps. Contains secrets, so it's excluded from project export by default.

---

## 3. Workflow

> ### ⚠️ How to pass files to platform MCP tools (READ FIRST)
>
> SnapCode uses the **cloud MCP (HTTP transport)** by default — the platform MCP
> server runs **remotely**, so it **cannot see your local files**. Every tool that
> takes a file does so by **content**, not by path. `Read` the file yourself, then
> pass its contents:
>
> **`import_pipeline` / `validate_pipeline` / `execute_pipeline`:** `Read` the `.slp`
> and pass its JSON as `slp_content`. Do NOT pass a file path. (`slp_file_path` only
> exists on the stdio/local-Docker transport; on the cloud MCP it isn't available, and
> putting a path into `slp_content` fails with
> `Failed to parse SLP content as JSON: Expecting value: line 1 column 1`.)
>
> **`upload_sldb`:** `Read` the file and pass its contents as `file_content`. Do NOT
> pass a file path. For text files (`.expr`, `.json`, `.csv`) use the default
> `encoding='utf-8'`; for binary files, base64-encode the bytes and pass
> `encoding='base64'`. (`local_file_path` only exists on the stdio transport.)
>
> Your own `Read`, `Write`, and `Bash` calls (including `slpy translate`) still use
> normal host paths as usual.
>
> | Tool | Pass this |
> |---|---|
> | `import/validate/execute_pipeline` | `slp_content="<Read the .slp, pass its JSON>"` (NOT a path) |
> | `upload_sldb` | `file_content="<Read the file, pass its contents>"` (+ `encoding`) (NOT a path) |

Always follow these steps in order. Never skip a step.

### Step 1 — Translate from .py (ALWAYS)

**Always re-translate from the `.py` source — never deploy a pre-existing `.slp` without re-translating first.** The `.slp` may be stale.

If only a `.slp` exists with no `.py`, skip to Step 3.

```bash
slpy translate -src {pipeline}.py -dest {pipeline}.slp -strict
```

Fix any translation errors before proceeding. Do not deploy a pipeline that fails translation.

### Step 2 — Pre-flight: upload supporting files

Before importing the pipeline, scan the `.py` source for any files it references and upload them to SLDB. Do this proactively — don't wait for validation to fail.

#### 2a — Expression libraries

Scan for `ExpressionLibraries(expression_library=[...])` in the `.py`. For each `.expr` file found, `Read` it and pass its contents:

```
upload_sldb(org="{org}", project_path="{path}", sldb_file_name="{name}.expr", file_content="<the .expr file's contents>")
```

`.expr` files are text, so the default `encoding='utf-8'` is correct — see the file-passing box above.

#### 2b — Input data files

Scan for `BinaryFileReader`, `FileReader`, or similar snaps with a `file_path` parameter pointing to a local file. For each file found, offer to upload it to SLDB. `Read` the file and pass its contents:

```
upload_sldb(org="{org}", project_path="{path}", sldb_file_name="{name}", file_content="<the file's contents>")
```

Text files (`.json`, `.csv`, `.jsonl`) use the default `encoding='utf-8'`. For binary files, base64-encode the bytes and pass `encoding='base64'` — see the file-passing box above.

If the user declines, note that the snap's file path will need to be set manually on the platform.

### Step 3 — Discover org, path, and snaplex

Resolve **org**, **project_path**, and **snaplex** — three distinct things (see §2). In order of preference:

1. Check saved user preferences — `default_org`, `default_path`, and snaplex may already be stored.
2. Determine the **org** (the tenant — not a project name; see §2). Then call `list_snaplexes(org="{org}")` to discover snaplexes. **Always pass the org explicitly** — omitting it, or passing a project name in its place, returns a 404.
3. Determine the **project_path** (where the pipeline is stored) and the snaplex — ask the user if still unclear.

> **org, project_path, and snaplex have no built-in defaults.** import/validate/execute require `org` + `project_path` (the platform addresses assets as `{org}/{project_path}/{name}`); validate/execute also require a snaplex (`snaplex_path`, a `runtime_path_id`). The tools fall back to `default_org` / `default_path` / `default_snaplex` **only** if `save_user_preferences` was called earlier **in the current session** — those defaults are in-memory, do NOT persist across MCP reconnects or Claude Code restarts, and are NOT inferred from a previous deploy. When they aren't set:
> - **Ask the user to confirm the org — never guess it.**
> - **Discover the snaplex** with `list_snaplexes(org="{org}")` and use its `runtime_path_id`; never invent one (a `runtime_path_id` is org-specific).
> - Once resolved, offer to `save_user_preferences` so later steps in the same session can omit them.

### Step 4 — Confirm with user before deploying

**Always pause and ask for confirmation before importing.** Show a deployment plan and wait for explicit approval. Never deploy silently.

Present the following and ask "Proceed?":

```
Ready to deploy:

  Pipeline  : {pipeline_name}
  File      : {repo_relative_path}/{pipeline}.slp
  Org       : {org}
  Path      : {path}
  Snaplex   : {snaplex_name} ({runtime_path_id})
  Overwrite : yes / no (pipeline already exists / new pipeline)

  Supporting files to upload:
    - {name}.expr  →  sldb:///{org}/{path}/
    - {name}.jsonl →  sldb:///{org}/{path}/   (if applicable)

Proceed? (yes / change org / change path / change snaplex)
```

If the user asks to change any field, update it and show the summary again before proceeding. Only import once the user confirms with "yes" (or equivalent).

### Step 5 — Import (deploy)

**`Read` the `.slp` file and pass its contents as `slp_content` — do NOT pass `slp_file_path`.** With the cloud MCP (HTTP transport) the server runs remotely and cannot see your local files, so it only accepts `slp_content` (raw JSON string). Passing a path into `slp_content` fails with `Failed to parse SLP content as JSON: Expecting value: line 1 column 1`.

1. `Read` the `.slp` file into memory (a normal host path is fine for your own `Read`).
2. Pass that JSON string as `slp_content`:

```
import_pipeline(slp_content="<the .slp file's JSON contents>", org="{org}", project_path="{path}")
```

> Note: `slp_file_path` only exists on the stdio (local-Docker) transport, not on the cloud MCP. `slp_content` works on both, so always use it.

If import fails with "pipeline already exists", ask the user whether to overwrite, then re-run with `duplicate_check=False`.

On success: note the pipeline name returned. Proceed immediately to Step 6 — do not stop here.

### Step 6 — Validate (MANDATORY after every deploy)

Always validate immediately after import. Never skip this step.

```
validate_pipeline(pipeline_name="{pipeline_name}", org="{org}", project_path="{path}", snaplex_path="{runtime_path_id}")
```

**Always pass `snaplex_path`** — validation will fail without it.

#### Parsing the validation response

The validation response can be very large (100KB+). Extract only these fields — do not process the full response:

| Field | Where to find it | What to report |
|-------|-----------------|----------------|
| `status` / `state` | top level | Completed / Failed |
| `error_count` | top level | number of errors |
| `documents_count` | top level | documents processed |
| `snap_errors` | `snap_statuses` where `error_count > 0` | snap label + error message |
| `inputs` | `input_views` | list with schemas, or "none" |
| `outputs` | `output_views` | list with schemas, or "none" |

**Never report "validation passed" without also reporting inputs, outputs, error count, and any warnings.**

#### Validation passed with no inputs/outputs

If validation passes but `input_views` and `output_views` are empty:
- Report this explicitly.
- Check if it's expected: pipelines that read/write directly to files (BinaryFileReader/Writer) have no exposed views — this is normal.
- If the pipeline is expected to have views (e.g. a triggered pipeline), flag it to the user.

### Step 7 — Fix and iterate (if validation fails)

If validation returns errors:

1. **Map each error to its source** — identify which snap and parameter is at fault using the snap label from the error.
2. **Fix the `.py` source** — always fix the SLPy source, never the `.slp` directly.
3. **Re-translate** — run `slpy translate -strict` again (Step 1).
4. **Re-upload supporting files if changed** (Step 2).
5. **Re-import without confirmation** — `Read` the freshly re-translated `.slp` and pass it as `slp_content` with `duplicate_check=False` to overwrite in place. No need to ask again for fix iterations, the user already approved the target.
6. **Re-validate** (Step 6).
7. **Repeat** until validation passes with no errors.

After each iteration, report:
- What error was found
- What change was made to the source
- Current validation status

**Maximum iterations: 5.** If validation still fails after 5 attempts, stop and present the remaining errors to the user with a clear explanation of what could not be resolved automatically.

---

## 4. Error Reference

### Import errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Failed to parse SLP content as JSON: Expecting value: line 1 column 1` | A file **path** was passed as `slp_content` (the cloud MCP has no `slp_file_path`) | `Read` the `.slp` and pass its JSON **contents** as `slp_content`, not a path |
| `slp_content is required` / unexpected `slp_file_path` argument | Called `import/validate/execute_pipeline` with `slp_file_path` on the cloud MCP | `Read` the `.slp` and pass `slp_content` instead |
| `file_content is required` / unexpected `local_file_path` argument (upload_sldb) | Called `upload_sldb` with `local_file_path` on the cloud MCP | `Read` the file and pass its contents as `file_content` (use `encoding='base64'` for binary) |
| `permission denied` / `path does not exist` | Wrong org or path | Re-run `list_snaplexes` with explicit org |
| `pipeline already exists` | Pipeline with same name exists at that path | Use `duplicate_check=False` to overwrite, or ask user to rename |

### Validation errors

| Error pattern | Likely cause | Fix |
|---------------|--------------|-----|
| `Unable to import expression library: {name}.expr` | `.expr` file not uploaded to SLDB | Upload via `upload_sldb` (Step 2a), re-validate |
| `Missing property value` on `filePath` | File path is empty — not set at all | Check the snap config in `.py` has a `file_path` value |
| `No snaplex configured` | `snaplex_path` not passed to `validate_pipeline` | Always pass `snaplex_path` explicitly |
| `output view missing` | Mapper or Transform snap has no output view defined | Add output view in the snap config |
| `input view missing` | First snap or router has no input defined | Add input view |
| `snap not found` | Invalid snap name survived translation | Check snap name against pygen |
| `expression error` | Invalid SEL expression | Fix expression syntax in `.py`, re-translate |
| `type mismatch` | Incompatible connection between snaps | Add appropriate formatter/parser snap |

---

## 5. Reporting to the User

After completing the loop, always report:

```
Deploy summary
──────────────
Pipeline  : {pipeline_name}
Org/Path  : {org}/{path}
Snaplex   : {runtime_path_id}
Status    : Validation passed ✓  (or: Failed after {N} iterations)
Documents : {documents_count}

Inputs    : {list with schemas, or "none (expected — no exposed views)"}
Outputs   : {list with schemas, or "none (expected — no exposed views)"}
Warnings  : {list or "none"}
```

After a successful deploy, ask the user:
- **Save preferences:** "Would you like to save `{org}`, `{path}`, and `{snaplex}` as defaults for future deploys?"
  Only call `save_user_preferences` if the user says yes.
- **Execute:** "Would you like to run it now with `execute_pipeline`?"
- **Schema concern:** If inputs/outputs look unexpected — "The schema looks unexpected — want to revisit the Mapper output?"
