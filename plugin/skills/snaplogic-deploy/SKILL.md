---
name: snaplogic-deploy
description: "Deploy, validate, and iteratively fix SnapLogic pipelines on the Control Plane. Covers the full loop: translate .py → .slp, upload supporting files, import to platform, validate, surface errors, fix source, repeat until validation passes."
tools: Read, Write, Bash, TodoWrite, mcp__snaplogic-platform__import_pipeline, mcp__snaplogic-platform__validate_pipeline, mcp__snaplogic-platform__execute_pipeline, mcp__snaplogic-platform__list_snaplexes, mcp__snaplogic-platform__save_user_preferences, mcp__snaplogic-platform__upload_sldb
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

## 2. Workflow

> ### ⚠️ File-path convention for platform MCP tools (READ FIRST)
>
> The platform MCP tools (`upload_sldb`, `import_pipeline`, `validate_pipeline`,
> `execute_pipeline`) run **inside a Linux container**, not on your host machine.
> They open file-path arguments (`local_file_path`, `slp_file_path`) **as the
> container sees them** — so you must pass a path that is valid inside the container,
> NOT a host path.
>
> **Rule: for these tools' file-path arguments, pass a path RELATIVE to the repo
> root** (e.g. `demo/csv_to_json.slp`, `libs/utils.expr`). The container's working
> directory is the repo root, so relative paths resolve correctly in every mode
> (Terminal + Docker on macOS/Windows, and the VS Code Dev Container).
>
> **Do NOT pass host absolute paths to these tools.** A Windows host path like
> `C:\Users\you\snapcode\demo\file.slp` does not exist inside the Linux container
> and will fail with "File not found". (A macOS path like `/Users/you/...` also will
> not match the container path.)
>
> This applies ONLY to the platform MCP tool arguments. Your own `Read`, `Write`,
> and `Bash` calls (including `slpy translate`) still use normal host paths as usual.
>
> | Tool argument | Pass this | Not this |
> |---|---|---|
> | `slp_file_path` | `demo/pipeline.slp` | `C:\Users\you\snapcode\demo\pipeline.slp` |
> | `local_file_path` | `libs/utils.expr` | `/Users/you/snapcode/libs/utils.expr` |

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

Scan for `ExpressionLibraries(expression_library=[...])` in the `.py`. For each `.expr` file found:

```
upload_sldb(org="{org}", sldb_path="{path}", sldb_file_name="{name}.expr", local_file_path="{repo_relative_path}/{name}.expr")
```

`local_file_path` is **relative to the repo root** (e.g. `libs/{name}.expr`) — see the file-path convention box above.

#### 2b — Input data files

Scan for `BinaryFileReader`, `FileReader`, or similar snaps with a `file_path` parameter pointing to a local file. For each file found, offer to upload it to SLDB:

```
upload_sldb(org="{org}", sldb_path="{path}", sldb_file_name="{name}", local_file_path="{repo_relative_path}/{name}")
```

`local_file_path` is **relative to the repo root** (e.g. `data/{name}`) — see the file-path convention box above.

If the user declines, note that the snap's file path will need to be set manually on the platform.

### Step 3 — Discover org, path, and snaplex

Resolve where to deploy and which snaplex to use. In order of preference:

1. Check saved user preferences — org, path, and snaplex may already be stored.
2. Ask the user for the org if not known. Then call `list_snaplexes(org="{org}")` to discover available snaplexes. **Always pass the org explicitly** — calling without an org will return a 404.
3. Ask the user for path and snaplex if still unclear.

**Default path:** `shared/`

**Default snaplex for validation:** prefer `cloud-dev` (`snaplogic/rt/cloud/dev`) if available.

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

```
import_pipeline(slp_file_path="{repo_relative_path}/{pipeline}.slp", org="{org}", project_path="{path}")
```

Use a path **relative to the repo root** for `slp_file_path` (e.g. `demo/{pipeline}.slp`) — see the file-path convention box at the top of the workflow. Do not pass a host absolute path; the tool resolves it inside the container.

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
5. **Re-import without confirmation** — use `duplicate_check=False` to overwrite in place. No need to ask again for fix iterations, the user already approved the target.
6. **Re-validate** (Step 6).
7. **Repeat** until validation passes with no errors.

After each iteration, report:
- What error was found
- What change was made to the source
- Current validation status

**Maximum iterations: 5.** If validation still fails after 5 attempts, stop and present the remaining errors to the user with a clear explanation of what could not be resolved automatically.

---

## 3. Error Reference

### Import errors

| Error | Cause | Fix |
|-------|-------|-----|
| `file not found` | Host path passed instead of a repo-relative path, or file not under the repo root | Pass a path relative to the repo root (e.g. `demo/x.slp`); the tool resolves it inside the container. The file must live under the repo directory so it's visible in the mount. |
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

## 4. Reporting to the User

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
