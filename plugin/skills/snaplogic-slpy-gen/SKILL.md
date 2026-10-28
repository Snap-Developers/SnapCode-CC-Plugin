---
name: snaplogic-slpy-gen
description: "Generate SnapLogic SLPy pipelines and expression libraries. Uses pygen MCP tools for snap discovery/validation, then compiles with slpy translate -strict via Bash."
tools: Read, Write, Bash, TodoWrite, Glob, Grep, mcp__snaplogic__pygen_query_pipeline_examples, mcp__snaplogic__pygen_query_snap_examples, mcp__snaplogic__pygen_validate_snap_names, mcp__snaplogic__pygen_get_snap_parameters, mcp__snaplogic__pygen_get_snap_documentation, mcp__snaplogic__pygen_validate_connections, mcp__snaplogic__pygen_list_snaps_by_category, mcp__snaplogic__pygen_get_snap_io_info, mcp__snaplogic__pygen_get_all_snap_names
---

# SnapLogic SLPy Pipeline Generator


## 1. Overview

Generate production-ready SnapLogic pipelines in Python format (SLPy) and expression libraries (.expr) with comprehensive snap discovery, validation, and reference documentation.

SLPy is a **declarative format** (not executable Python) that must be converted to SLP JSON using the slpy CLI for import into SnapLogic. This skill automates the entire generation and validation workflow using pygen MCP tools.

Beyond static validation, SLPy pipelines can OPTIONALLY be **executed locally** with `slpy exec` against a subset of supported snaps — the one check that exercises runtime data flow and transformation logic. It's optional but the strongest quality lever: reach for it whenever the pipeline does real transform/expression work and the snaps are execution-supported; skip it when there's nothing to exercise (pure pass-through). When a source/sink snap is unsupported (Salesforce, Snowflake) or makes a live external call (`APISuiteHTTPClient`), build a **test segment pipeline** so you can still exec offline and reproducibly. To replace the SOURCE, **prefer a `TransformJSONGenerator` with inline `editable_content`** (data embedded in the snap — no separate file, no `file_path` to get wrong); use `BinaryFileReader` + a written sample file only when the transforms genuinely need binary/CSV input. Replace an unsupported SINK with `TransformJSONFormatter` + `BinaryFileWriter`. Keep all transform snaps identical. Skip execution when there's nothing to exercise — a pure pass-through, or a trivial pipeline the translator already fully validated. Keep executing while each run surfaces a new runtime bug you can fix; stop once it passes, an error repeats, or only cosmetic issues remain (a zero exit code does not by itself prove correctness, so don't re-run just to double-check a green result). Delete any scratch/debug/test pipeline you create before finishing.

### File Naming Rules

SLPy pipeline files MUST use the `.py` extension. The slpy CLI rejects all other extensions.

- **SLPy source files**: `{name}.py` (e.g., `countries_analysis.py`) — NOT `.slpy`, NOT `.slpy.py`
- **SLP output files**: `{name}.slp` (e.g., `countries_analysis.slp`) — NOT `.json`, NOT `.pipeline`
- **Expression libraries**: `{name}.expr` (e.g., `helpers.expr`)

The `.slp` file IS JSON (SnapLogic's native pipeline format). Do not use `.json` — always use `.slp`.

### File Path Rules (SnapLogic Asset Paths)

When a pipeline references SnapLogic assets by path (input files, output files, expression library `file_` params, `FlowPipelineExecute.pipeline`, etc.), **use the asset-store form and strip any absolute filesystem prefix**.

- ✅ `"input.csv"`
- ❌ `"/tmp/workspace/snaplogic/projects/share/input.csv"`

SnapLogic's asset store resolves paths relative to the org/project root, not to the filesystem the pipeline was generated on. An absolute path embeds a machine-local location into the pipeline and breaks asset resolution when the pipeline runs on the platform.

This applies to **generation and refinement** alike: when updating an existing pipeline, keep paths in the asset-store form even if you read the file from an absolute path during local validation.

#### Strip the org/project prefix — use only the filename

When the user gives you a path in the SnapLogic asset-store form `org/project_space/project/<file>` or `org/shared/<file>`, configure the snap with **only the basename** — not the full path. The pipeline runs scoped to its project, so the org/project prefix is already implicit. Putting it back in `file_path=` makes the snap look outside its own project and breaks asset resolution.

- ✅ `BinaryFileReader(file_path='customers.csv')` — user gave `acme/sales/onboarding/customers.csv`
- ✅ `BinaryFileReader(file_path='customers.csv')` — user gave `acme/shared/customers.csv`
- ❌ `BinaryFileReader(file_path='acme/sales/onboarding/customers.csv')` — full path leaked into snap config
- ❌ `BinaryFileReader(file_path='acme/shared/customers.csv')` — same problem with the `shared` form

If the user references a file in a subfolder *inside* their project (`acme/sales/onboarding/raw/customers.csv`), keep only the part after the project segment: `raw/customers.csv` — never the org/space/project prefix.

The same rule applies to `ExpressionLibraries.ExpressionLibraryItem(path=...)`: configure the item with **only the basename**, not the org/project prefix.

- ✅ `ExpressionLibraryItem(path='helpers.expr', as_='lib')` — user gave `acme/sales/onboarding/helpers.expr`
- ✅ `ExpressionLibraryItem(path='helpers.expr', as_='lib')` — user gave `acme/shared/helpers.expr`
- ❌ `ExpressionLibraryItem(path='acme/sales/onboarding/helpers.expr', as_='lib')` — full path leaked
- ❌ `ExpressionLibraryItem(path='acme/shared/helpers.expr', as_='lib')` — same problem with the `shared` form

#### Writer output paths — DO NOT invent containing folders

Folders in SnapLogic projects are **not** auto-created by writer snaps. If a writer's `filename` points into a folder that doesn't exist in the user's project, the pipeline runs but the write fails at execution time, and the user has to go create the folder by hand in the designer (which is awkward — folders aren't a first-class object the way they are on a filesystem).

When the user says "write to `customers.csv`" or "save the output as `report.json`", configure the writer with **exactly that path** — no leading directory, no `output/` prefix, no `data/` prefix, no timestamped subfolder.

- ✅ `BinaryFileWriter(filename='customers.csv', ...)` — user said `customers.csv`
- ❌ `BinaryFileWriter(filename='output/customers.csv', ...)` — invented `output/` folder
- ❌ `BinaryFileWriter(filename='exports/2026/customers.csv', ...)` — invented `exports/2026/` folder

**Add a containing folder ONLY when the user explicitly asks for one** ("save it under `reports/`", "put outputs in a `cleaned/` folder"). When in doubt, mirror exactly what the user said and let them add structure later through follow-up requests.

The same rule applies to `BinaryFileReader` — don't invent an `inputs/` prefix for an input filename the user gave you bare. And to `FlowPipelineExecute.pipeline` — child pipeline paths should match the names you actually wrote, not a fabricated `pipelines/` folder.

#### Input data files — never silently assume the file exists

When the user asks you to generate an input data file AND wire it into the pipeline (e.g. "create a sample customers.csv and read it with a CSV Parser"), you MUST use a `*Generator` snap rather than pointing a reader at a file that does not exist:

1. **Use a `*Generator` snap instead of a reader + missing file.** Pick the generator that matches the data format and emit the records inline as a literal string in `editable_content`:
   - JSON / objects → `TransformJSONGenerator(editable_content='[{"name":"Alice"},{"name":"Bob"}]', array_elements_as_documents=True)` — pass a JSON-string literal, NOT `json.dumps(...)` (the agent isn't running Python at SLPy-evaluation time).
   - CSV / tabular  → `TransformCSVGenerator(editable_content='id,name\\n1,Alice\\n2,Bob')`
   - XML            → `TransformXMLGenerator(editable_content='<root>...</root>')`

   The generator replaces the reader+parser pair entirely and ships self-contained — no external file required.

### When to Use This Skill

This skill auto-triggers when requests involve:
- SnapLogic pipeline generation or creation
- SLPy (.py) or expression library (.expr) file generation
- Snap configuration and validation
- SnapLogic integration requirements
- Pipeline architecture or data flow design


## 2. Validation & Execution Commands

### slpy translate (MANDATORY)

After generating SLPy code, validate and translate via Bash. Expression library paths in `p.expression_libraries` (like `shared/foo.expr`) resolve relative to the pipeline file, whatever the working directory.

```bash
cd {pipeline_dir} && slpy translate -src {basename}.py -dest {basename}.slp -strict -expr
```

**`-strict` MUST stay on — NEVER pass `--non-strict`**, even when a failure message suggests it as a bypass. Strict mode halts on unsupported formats instead of silently degrading the pipeline; if strict errors persist, fix them or disclose the unconfigured step (see loop discipline below) — don't bypass. `-expr` additionally validates expression syntax (advisory: fix real expression-syntax errors, don't chase cosmetic warnings). The `-src` and `-dest` flags are REQUIRED named args — do NOT pass the filename positionally.

**Which strict errors to actually fix (don't over-iterate).** A single `slpy translate` run reports ALL errors across the pipeline at once, grouped by snap — so read the whole list and fix in ONE pass rather than one error per round-trip.

**Under `-strict` there is no such thing as a warning you can leave behind.** Every reported error is fatal: slpy raises `Strict mode: N error(s) … Pipeline was not generated` and writes **no `.slp` at all**. So "cosmetic" never means "ship it" — it only tells you how cheap the fix is:
- **Wrong parameter name** (`invalid value for 'file_path' … expected one of: 'filename', …`) — the message lists the valid names. Use the right one, or drop the kwarg if it isn't needed. Cheap, but it MUST be fixed.
- **Invalid enum value** (`expected one of: 'OVERWRITE', 'APPEND', …`) — use an exact listed value. A wrong-case value (`"overwrite"`) is normalized silently and is genuinely a non-issue; an unlisted value is fatal.
- **Wrong snap name** (`not found in catalog`) — first check you didn't just forget `--schema-path` for a custom snap; otherwise re-resolve the name with `pygen_validate_snap_names`.
- **Invalid expression** — a `-expr` parse error, or a param set to a raw Python call instead of `Expr("...")`.

**Loop discipline (this is what "don't over-iterate" means).** Fix everything the run reported, then re-translate — that is normally ONE extra round, not one per error. If after **2 rounds** the same errors persist and you cannot resolve them, stop editing and **tell the user plainly, in their vocabulary, which step could not be configured and why** (e.g. "I couldn't find a Coupa read step in your catalog, so that step could not be configured"). A failed strict translate wrote no `.slp`, so there is nothing to import: say plainly that the pipeline could not be produced and which step could not be configured. Never imply it was delivered. Never silently drop a parameter the user explicitly asked for (a batch size, a timeout, a write mode, a file name) — look up its real name rather than deleting it.

**Custom snaps: `--schema-path <path>` is MANDATORY whenever the pipeline uses custom snaps.** Signal: the user request contains a `## Custom Snap Definitions` and `## Translation` section. Every `slpy translate` invocation (including retries) MUST pass `--schema-path`:

```bash
cd {pipeline_dir} && slpy translate -src {basename}.py -dest {basename}.slp -strict -expr --schema-path {schema_path_from_request}
```

**Guard:** If neither `## Custom Snap Definitions` nor `## Translation` appears in the user request, ignore this section entirely — do not attempt to introduce custom snaps.

Without this flag, strict mode rejects custom snaps with `snap name '...' not found in catalog`. If you see that error on a snap defined in `## Custom Snap Definitions`, you forgot `--schema-path` — re-run with the flag instead of "fixing" the name.


**Round-trip edits: `--preserve-ids <original.slp>` is MANDATORY when the `.py` descends from an existing platform pipeline** (the user provided a platform-exported `.slp` that was translated to `.py`, or you are refining such a `.py`):

```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict --preserve-ids {original}.slp
```

Without the flag, translate mints fresh UUIDs for every snap — on re-import the platform sees a brand-new set of snaps instead of an edit, dropping all existing links and snap identity. With it, kept snaps retain their original UUIDs and canvas positions, new snaps get fresh UUIDs placed next to their neighbors, and removed snaps are dropped. Success prints a summary: `preserve-ids: 5 snap UUID(s) preserved, 1 fresh`.

- **Do not rename `snap_N` variables when editing an encoded `.py`** — the variable name is the join key back to the original snaps; renaming reads as delete + add and loses that snap's identity.
- The flag only applies to the `.py` → `.slp` direction, and composes with `-strict`, `-expr`, and `--schema-path`.
- Keep the original `.slp` export unmodified; pass the same file on every re-translate in the session.

Examples:
```bash
# File at workspace root
cd {workspace_root} && slpy translate -src countries_by_continent.py -dest countries_by_continent.slp -strict -expr

# File in a project subdirectory
cd {workspace_root}/acme/sales/onboarding && slpy translate -src countries_by_continent.py -dest countries_by_continent.slp -strict -expr
```

**Expected success output:** no output; `.slp` file is created.
**Expected error output:** `Error: Line 42: Invalid snap name 'BadSnapName'`

If you see `slpy: error: unrecognized arguments:` — you forgot the `-src` flag.

`slpy translate` loads every library in `p.expression_libraries` the way the platform does, with paths relative to the pipeline file:

- `Expression library file not found: <path>` — the `.expr` file is not at `<path>`. Create it there or fix the path.
- `Failed to load expression library '<alias>' from <path>: <reason>` — the platform would reject this import too. Fix the library at the line in `<reason>`; `slpy validate-expression` reports the same problem for the `.expr` file alone.

### slpy validate-expression (for .expr files)

```bash
slpy validate-expression -expr-lib {library_name}.expr
```

This validates expression library syntax separately from pipeline translation. Use this when generating or modifying `.expr` files to catch syntax errors before pipeline validation.

### slpy exec (OPTIONAL — recommended whenever it can catch a runtime bug)

`slpy exec` runs the pipeline against real/sample data and is the ONLY step that catches runtime errors static validation can't — raised exceptions from bad JSONPath, `$groupBy` field mistakes, expression-library failures, wrong field references, type coercion. It's optional, but it's the strongest quality lever you have, so **reach for it whenever the pipeline does real data processing** (any transform/expression/mapper/filter/router/group-by logic) and the snaps are execution-supported. Use judgment: skip it when there's nothing to exercise (a pure pass-through, or a trivial single-mapper the translator already fully validated), and don't force a run just to tick a box.

**When to skip / adapt:**
- Skip when there's nothing to exercise — a pure pass-through (e.g. a binary read→write with no parser/formatter/transform), or a trivial single-mapper the translator already fully validated.
- If a source/sink snap isn't execution-supported (Salesforce, Snowflake, DB) OR makes a live external call (`APISuiteHTTPClient`), build a test segment (Step 3 / see below) and exec that. Replace the SOURCE with a `TransformJSONGenerator(editable_content='[{...}]', array_elements_as_documents=True)` (inline data — the default, avoids a separate file + `file_path` fumble); fall back to `BinaryFileReader` + a sample file only for genuinely binary/CSV input. Replace an unsupported SINK with `TransformJSONFormatter` + `BinaryFileWriter`. Keep all transform snaps identical. This keeps the run reproducible and offline.

**Keep executing while you're making progress; stop when you're not.** Exec is a quality check, not a gate you must turn green — a zero exit code does NOT prove correctness (some runtime failures resolve to null instead of raising). There's no fixed run count: fixing a real runtime bug that exec surfaced (a raised exception, a mapper dropping all docs, a wrong JSONPath) is high-value — keep going through a genuine multi-bug chain. The rule is about *progress*, not a number:
- **Keep going** as long as each exec surfaces a NEW, concrete runtime error and you have a specific fix for it.
- **STOP** when: exec passes cleanly, OR the same error repeats (you're not converging), OR you'd be re-running just to double-check a green result, OR the only remaining issues are cosmetic. Don't chase a "cleaner" output once the data flows.
- Use `--verbose` on a run to inspect per-snap I/O rather than re-executing blindly.
- If you build a scratch/debug pipeline to inspect intermediate output, that's fine — but **delete it before finishing**. Only the real deliverable pipeline(s) should remain on disk — the test segment goes too.

When you run it, **`cd` into the pipeline's directory first** so relative reader/writer paths resolve the way the pipeline expects. Bundle with the translate step on the same Bash line to share one `cd`:

```bash
cd {pipeline_dir} && slpy translate -src {basename}.py -dest {basename}.slp -strict -expr && slpy exec {basename}.py
```

Standalone invocations:
```bash
# Basic execution
cd {pipeline_dir} && slpy exec {basename}.py

# With pipeline parameters (no underscore prefix in -e flag)
cd {pipeline_dir} && slpy exec {basename}.py -e param_name=value -e another_param=value2

# Dry run (shows pipeline structure and loaded expression libraries)
cd {pipeline_dir} && slpy exec {basename}.py --dry-run

# Verbose output (recommended for debugging)
cd {pipeline_dir} && slpy exec {basename}.py --verbose
```

**What it does:**
- Runs the pipeline locally, processing actual data through each snap
- Performs real file I/O (reads/writes local files)
- Makes real HTTP calls for `APISuiteHTTPClient` snaps (swap in a `TransformJSONGenerator` with inline sample data to stay offline)
- Validates transformation logic, data flow, and output correctness at runtime
- Loads expression libraries declared via `p.expression_libraries` — `lib.*` function calls in expressions are fully evaluated at runtime

**Prerequisites:**
1. Pipeline must pass `slpy translate` first (syntax must be valid)
2. All snaps in the pipeline must be execution-supported (check with `slpy exec --list-snaps`)
3. Input data files must exist at the specified paths
4. Pipeline parameters must be passed via `-e` flag if required
5. Expression library `.expr` files must exist at the paths declared in `p.expression_libraries` (resolved relative to the pipeline file)

**Limitations:**
- Only a subset of snaps are supported — run `slpy exec --list-snaps` to check the current list
- `APISuiteHTTPClient` IS execution-supported but makes **real network calls** — replace it with a `TransformJSONGenerator` carrying inline sample data (preferred), or `BinaryFileReader` + a written file for binary/CSV input
- No account or credential support (cannot authenticate to external systems)
- For pipelines with non-supported snaps, create a **test segment pipeline** replacing those snaps as above (see Checkpoint 7)

**IMPORTANT:** `slpy exec` is NOT a replacement for `slpy translate`. Both serve different purposes:
- `slpy translate` = syntax validation + .slp generation (MANDATORY)
- `slpy exec` = runtime validation of data flow (RECOMMENDED when feasible)

### Execution-Supported Snaps

The `slpy exec` command can run SLPy pipelines locally against a subset of supported snaps. To determine which snaps are currently supported:

```bash
slpy exec --list-snaps
```

This command returns the current list of execution-supported snaps. The list evolves over time as new snaps gain execution support, so **always run this command** rather than relying on a hardcoded list.

**How to use in the workflow:**
1. Run `slpy exec --list-snaps` to get the current supported snap list
2. Compare the pipeline's snaps against the supported list
3. If all snaps are supported → pipeline is fully executable
4. If some snaps are not supported → create a test segment pipeline: replace the source with a `TransformJSONGenerator` holding inline sample data (preferred) or `BinaryFileReader` for binary/CSV, and an unsupported sink with `TransformJSONFormatter` + `BinaryFileWriter` (see Checkpoint 7)

**Notable execution-supported snaps:** `Script` (runs Python scripts in a sandboxed environment — same ScriptHook API as the platform), `FlowPipelineExecute` (runs child `.py` pipelines locally). These do NOT require test segment workarounds.

**Key note:** `APISuiteHTTPClient` is execution-supported but makes **real network calls** — replace it with a `TransformJSONGenerator` carrying inline sample data (preferred — no data file, no `file_path` to get wrong), or `BinaryFileReader` + a written file only when the transforms genuinely need binary/CSV input. Either keeps the run offline and reproducible.

### Pygen MCP Tools Used for Validation

**The only pygen MCP tools you should use:**

- `pygen_validate_snap_names(do_get_parameters=True)` - ONE batched call for Checkpoint 1: pass ALL candidate snap names, get canonical names + their parameters

- `pygen_validate_snap_names` - Validate snap names BEFORE generation (Checkpoint 1); pass `do_get_parameters=True` to get their parameters in the same call
- `pygen_validate_connections` - For validating pipeline structure (snap names + connection type compatibility) before full code generation (Checkpoint 1.5)

- `pygen_list_snaps_by_category` - For discovering available snaps by category/pack (deterministic filter)
- `pygen_query_*` - For discovering snaps and patterns (vector search)
- `pygen_get_*` - For retrieving snap documentation and parameters

## 3. Workflow Patterns

### Quick Start Decision Tree

Before starting, assess complexity and choose the appropriate workflow pattern:

#### Step 0: Assess Complexity

**Questions to ask:**
- Is this a simple linear pipeline (<5 snaps, single domain)?
- Multiple integrations or transformations involved?
- Complex orchestration, error handling, or ELT?
- Modifying an existing pipeline?


#### Pattern 0: Express Mode (Target: 3 calls)
**Use for:** Simple source→dest transformations
- CSV to JSON conversion
- API to database load
- Single-stage ETL

**Workflow:**
1. `pygen_query_pipeline_examples("combined intent")`
2. `pygen_validate_snap_names([ALL candidate snaps], do_get_parameters=True)` — canonical names + params in one call
3. `pygen_get_snap_documentation([connectivity snaps + any `*Lookup` / `*Select` / `*Execute`])` — the re-rooting families are required here too, see Checkpoint 2
4. Generate SLPy (file MUST have .py extension) → Validate with Bash: `cd <pipeline_dir> && slpy translate -src X.py -dest X.slp -strict -expr`
5. Optional: for a simple source→dest pipeline, `slpy translate -strict -expr` is usually sufficient. If it has any non-trivial transform/expression logic, exec it (`cd <pipeline_dir> && slpy exec X.py`, bundled on the translate line) to confirm the data flows; build a quick test segment if the source is a live/unsupported snap. `rm` any scratch/test `.py` before finishing.

#### Pattern 1: Simple Pipeline (Target: 5-6 calls)
**Use for:** Standard ETL with known snaps
- Multi-step transformations
- Basic data quality checks
- Single source, single destination

**Workflow:**
1. `pygen_query_pipeline_examples("combined intent")`
2. `pygen_validate_snap_names([ALL candidate snaps], do_get_parameters=True)` — canonical names + params in one call
3. `pygen_validate_connections(skeleton_slpy)` — validate snap names + connection type compatibility
4. `pygen_get_snap_documentation([connectivity snaps + any `*Lookup` / `*Select` / `*Execute`])` — the re-rooting families are required here too, see Checkpoint 2
5. `pygen_get_snap_parameters([connectivity_snaps_only])` — only if the Checkpoint 1 params were insufficient
6. Generate SLPy (file MUST have .py extension) → Validate with Bash: `cd <pipeline_dir> && slpy translate -src X.py -dest X.slp -strict -expr`
7. Optional but recommended given the transform logic: `cd <pipeline_dir> && slpy exec X.py` (all-supported), or build a test segment `X_test.py` and exec that if a source/sink snap is unsupported or makes a live call. Skip for pure pass-through. Keep fixing+re-running while exec surfaces new runtime bugs; stop when it passes or stalls. `rm` any scratch/test `.py` before finishing.

#### Pattern 2: Complex Pipeline (Target: 6-8 calls)
**Use for:** Advanced integration scenarios
- Multi-stage transformations with routing
- Specialized integrations (Salesforce, SAP, NetSuite)
- Error handling and orchestration
- ELT patterns with database pushdown

**Workflow:**
1. `pygen_query_pipeline_examples("primary segment")` — add `filter_packs` when the target system is known
2. `pygen_query_snap_examples("specialized integrations")` — or `pygen_list_snaps_by_category(pack="Snowflake")` if you know the target system but need to discover available snaps
3. `pygen_validate_snap_names([ALL candidate snaps], do_get_parameters=True)` — canonical names + params in one call
4. `pygen_validate_connections(skeleton_slpy)` — validate snap names + connection type compatibility
5. `pygen_get_snap_documentation([connectivity snaps + any `*Lookup` / `*Select` / `*Execute`])` — the re-rooting families are required here too, see Checkpoint 2
6. `pygen_get_snap_parameters([connectivity_snaps_only])` — only if the Checkpoint 1 params were insufficient
7. Generate SLPy (file MUST have .py extension) → Validate with Bash: `cd <pipeline_dir> && slpy translate -src X.py -dest X.slp -strict -expr`
8. Recommended (complex transforms benefit most from a runtime check): `cd <pipeline_dir> && slpy exec X.py` if all snaps are supported, else build a test segment `X_test.py` (source → `TransformJSONGenerator` with inline data; unsupported sink → `TransformJSONFormatter` + `BinaryFileWriter`; transforms identical) and `slpy exec X_test.py`. Keep fixing+re-running while exec surfaces new runtime bugs (complex transforms often need a few passes); stop when it passes or stalls. `rm` any scratch/test `.py` before finishing.

#### Pattern 3: Refinement (Target: 1-3 calls)
**Use for:** Updating existing pipelines
- Modifying snap configurations
- Adding error handling
- Performance optimizations

**Workflow:**
1. Read existing .py file
2. If adding new snaps: `pygen_validate_snap_names([new_snap_candidates])` first (Checkpoint 1 applies to added snaps too), then `pygen_get_snap_documentation([...])` for the connectivity ones only
3. Apply modifications (file MUST have .py extension) → Validate with Bash: `cd <pipeline_dir> && slpy translate -src X.py -dest X.slp -strict -expr`
4. Optional: only if the change touched non-trivial transform logic AND all snaps are execution-supported, re-run `cd <pipeline_dir> && slpy exec X.py`. Skip for config-only tweaks.

**If the pipeline came from the platform** (a platform-exported `.slp` translated to `.py`), extra rules apply to every refinement:

- Translate with `--preserve-ids <original>.slp` (see §2) so snap UUIDs, links and canvas positions survive re-import, and keep the existing `snap_N` variable names.
- Preserve account bindings you were not asked to change — in particular `pm_account=Expr('lib.env.*')` expression refs (see `references/accounts.md`).

**Refinement discipline:** change only what the instruction requires — do not reformat, reorder, or renumber `snap_N` variables, and do not re-emit or alter settings of snaps the request doesn't touch.

### Tool Efficiency Rules

1. **Snap name resolution is mandatory** - Always resolve snap names using `pygen_validate_snap_names(do_get_parameters=True)` (ONE batched call for ALL candidates) before generation (this is different from final pipeline translation via slpy CLI)
2. **Documentation is selective** - Get snap documentation using `pygen_get_snap_documentation` for **connectivity snaps** (Enterprise, database, cloud storage, HTTP) **and LLM/agent snaps** (agent, prompt-generator, function-generator — their fields differ per provider and are not guessable) **only**. Transform and Flow snap documentation is deferred until needed (see Checkpoint 2).
3. **Account check for connectivity snaps (MANDATORY)** - When your pipeline includes connectivity snaps (HTTP Client, database, SaaS integrations), you MUST read `references/accounts.md` and follow its workflow BEFORE generating code. Never use pipeline parameters for credentials when an Account asset is available in the workspace.
3b. **Pattern check (MANDATORY)** - Before choosing how to generate and before writing any code, scan the **Pipeline Patterns** table at the end of this file. If the request asks for what a row describes, you MUST read that pattern's SKILL.md BEFORE generating code. Patterns are multi-pipeline bundles (one file each) built from fixed-format boilerplate — do not derive the topology from memory; their working examples live in each pattern's `references/`.
4. **Maximum 8 MCP tool calls** - Generate with available information, iterate if needed
5. **No duplicate MCP calls** - Never call the same pygen tool with the same or overlapping query twice. If you need more examples, use a DIFFERENT query string, not a repeat.
6. **Read format reference BEFORE writing code** - When using pipeline parameters (`ParamTable`), expression libraries, error pipelines, or unfamiliar connection patterns, read the relevant reference file BEFORE writing code. Prevention is cheaper than error recovery.
7. **Only import what you use** - Do not import `OPEN_VIEW` unless the pipeline has open input or output views. Most pipelines are fully connected and do not need it.
8. **Use tool-provided schemas, not memory** - The `expr` flag / `(expr)` marker in parameter schemas from `pygen_validate_snap_names` or `pygen_get_snap_parameters` tells you which params accept `Expr()`. Parameters without it expect plain strings. Don't guess from memory — there are 1,200+ snaps.
9. **Tool call targets by pattern:**
   - Express Mode: 3 calls
   - Simple: 5-6 calls (includes skeleton validation)
   - Complex: 6-8 calls (includes skeleton validation + optional snap discovery)
   - Refinement: 1-3 calls

### Pygen MCP Tool Reference

**Read `references/mcp_tool_reference.md` for detailed tool usage patterns, examples, and best practices.**

Quick reference:

| Tool | Purpose | Key Usage |
|------|---------|-----------|
| `pygen_query_pipeline_examples` | Find pipeline patterns via RAG | Pass 1-2 query strings; for a known target system add `filter_packs=["Snowflake"]` (single-query only; if a filtered query returns nothing, retry unfiltered) |
| `pygen_query_snap_examples` | Discover snaps via RAG | Returns snap names matching a query |
| `pygen_validate_snap_names` | Validate + fuzzy-correct snap names, with `do_get_parameters=True` their parameters too | ONE batched call for ALL candidate snaps (Checkpoint 1) |
| `pygen_get_snap_parameters` | Get snap config schemas | Only if the Checkpoint 1 params were insufficient |
| `pygen_get_snap_documentation` | Detailed snap docs | For connectivity snaps (Snowflake, REST, etc.) |
| `pygen_validate_connections` | Validate skeleton pipeline structure | Pass minimal SLPy with snap declarations + `p.connect()` |
| `pygen_list_snaps_by_category` | List snaps by category/pack | Use instead of RAG when you know the category |
| `pygen_get_snap_io_info` | Snap input/output view types | Planning connections; resolving type mismatches |
| `pygen_get_all_snap_names` | Every snap name in the catalog | Use sparingly — long list, consumes context |

**IMPORTANT:** `slpy exec` is NOT a replacement for `slpy translate`:
- `slpy translate` = syntax validation + .slp generation (MANDATORY)
- `slpy exec` = runtime validation of data flow (RECOMMENDED when feasible)

### Selective Documentation Strategy

#### Snap Categorization: Connectivity vs Transform/Flow

Categorize each candidate snap to determine whether to fetch documentation eagerly or defer it:

| Category | Fetch docs eagerly? | Examples |
|----------|-------------------|----------|
| **Database** | Yes | Snowflake*, PostgreSQL*, MySQL*, Oracle*, SQL Server*, BigQuery*, Redshift*, MongoDB* |
| **Enterprise SaaS** | Yes | Salesforce*, NetSuite*, SAP*, ServiceNow*, Workday*, HubSpot*, Dynamics* |
| **Cloud Storage** | Yes | BinaryS3File*, APISuiteHTTPClient (Azure/GCP) |
| **HTTP/API** | Yes | APISuiteHTTPClient |
| **Transform** | No — defer | TransformMapper, TransformGroupBy*, TransformAggregate, TransformJoin, TransformJSON*, TransformCSV*, TransformXML* |
| **Flow** | No — defer | FlowFilter, FlowRouter, FlowCopy, FlowGate, FlowSequence, FlowPipelineExecute |
| **File I/O** | No — defer | BinaryFileReader, BinaryFileWriter |
| **Parse/Format** | No — defer | Binary*Parser, Binary*Formatter, Transform*Parser, Transform*Formatter |

The wildcard `*` means "any snap name starting with this prefix".

**Why selective documentation:**
- Connectivity snaps have complex, varied configuration (auth, connection strings, query syntax, bulk modes) not covered by the skill's static references
- Transform/Flow snaps follow consistent patterns documented in this skill's reference sections
- Deferring transform/flow documentation reduces latency and context window usage

## 4. Validation Checkpoints

**Read `references/validation_checkpoints.md` for full checkpoint details with code examples.**

Follow these checkpoints sequentially. Checkpoints 1-6 are for syntax/structure. Checkpoint 7 (execution) is optional but recommended.

| # | Checkpoint | Tool/Command | Required |
|---|-----------|-------------|----------|
| 1 | **Snap Name Resolution** | `pygen_validate_snap_names(do_get_parameters=True)` — ONE batched call for ALL candidates: canonical names + exact parameter names (prevents parameter guessing errors) | MANDATORY |
| 1.5 | **Connection Validation** | `pygen_validate_connections` (skeleton SLPy) | REQUIRED for branching pipelines (router/join/union/copy); RECOMMENDED otherwise |
| 2 | **Snap Documentation** | `pygen_get_snap_documentation` / `pygen_get_snap_parameters` | Connectivity snaps, AND any snap that re-roots its input (`*Lookup`, `*Select`, `*Execute` — see Rule 11) |
| 3 | **Script Snap Review** | Manual review | If Script Snap present |
| 4 | **Child Pipeline Validation** | Manual review | If FlowPipelineExecute present |
| 4b | **File Extension Check** | Manual | MANDATORY (`.py` for source, `.slp` for dest) |
| 5 | **SLPy Translation** | `slpy translate -src X.py -dest X.slp -strict -expr` via Bash (`-expr` findings are advisory — fix real expression-syntax errors, don't chase cosmetic warnings). Any `WARNING` line translate prints to stderr IS blocking — see Checkpoint 5 | MANDATORY |
| 5b | **Expression Library Integration** | Manual checklist | If `.expr` file generated |
| 6 | **Expression Library Validation** | `slpy validate-expression -expr-lib X.expr` via Bash | If `.expr` file exists |
| 7 | **Execution Validation** | `slpy exec X.py` via Bash | OPTIONAL — recommended when the pipeline has real transform logic (build a test segment for unsupported/live source/sink); skip pure pass-through |

**Key rules:**
- Never skip Checkpoint 1 (snap validation) or 5 (slpy translate)
- For Checkpoint 2: fetch docs eagerly for **connectivity snaps** only (Snowflake, REST, etc.); defer transform/flow snap docs until errors occur
- For Checkpoint 5 errors: under `-strict` EVERY reported error is fatal (no `.slp` is written), so fix them all — read the full grouped list and correct it in one pass, then re-translate. Wrong param names and invalid enum values are cheap fixes, not skippable ones. If the same errors survive 2 rounds, tell the user which step couldn't be configured. No `.slp` was written, so there is nothing to import — say that plainly rather than implying a delivery. (See "Which strict errors to actually fix" under §2.)
- **Checkpoint 7 decision rule (execution is OPTIONAL but the strongest quality lever — use judgment):**
  - Pipeline has real transform/expression logic AND all snaps execution-supported → **run `slpy exec X.py`** (bundle on the translate Bash line). This is where exec earns its keep — it proves the data actually flows and the transforms produce what you expect.
  - Real transform logic but the source/sink is unsupported (Salesforce/Snowflake/DB) OR makes a live external call (`APISuiteHTTPClient`) → **build a test segment `X_test.py`** and exec it. Replace the SOURCE with `TransformJSONGenerator` (inline `editable_content` — preferred; no separate file/`file_path`), or `BinaryFileReader` + sample file only for binary/CSV. Replace an unsupported SINK with `TransformJSONFormatter` + `BinaryFileWriter`. Keep ALL transform snaps identical. Keeps the run reproducible and offline.
  - Skip execution when there's nothing to exercise: a pure pass-through, or a trivial pipeline the translator already fully validated. Don't force a run just to tick the box.
  - **Run as long as you're making progress, not a fixed count.** Exec is a quality check, not a gate — a green exit (0) does NOT prove correctness (some runtime failures resolve to null instead of raising). Keep fixing+re-running while each exec surfaces a NEW concrete runtime bug (a multi-bug transform chain legitimately needs several passes). STOP when exec passes, the same error repeats (not converging), or only cosmetic issues remain — don't re-run just to re-confirm a green result.
  - **Clean up:** building a scratch/debug pipeline to inspect intermediate output is fine, but `rm` it (and any test segment) before finishing — only the real deliverable pipeline(s) should remain.
  - If you execute: run `slpy exec --list-snaps` ONCE (no grep filters) for the supported list; rerun with `--verbose` to inspect per-snap I/O rather than creating debug pipelines.

## 5. Critical Generation Rules

**Read `references/critical_rules.md` for rules 1–9, 11 and 12 in full detail — they prevent 90% of SLPy generation errors. (Rule 10 is tool-usage guidance, given in full below.)**

Key rules summary (read the reference for complete details, examples, and edge cases):

1. **Expr() Wrapper Decision** — Contains `$field`, `_param`, or functions? Use `Expr()`. Plain literal? Don't.
2. **Type Compatibility Matrix** — binary→binary, document→document. Never cross types.
3. **HTTP/REST Operations** — Use `APISuiteHTTPClient` (not deprecated REST snaps).
4. **Script Snap Usage** — Last resort only. Use TransformMapper/FlowRouter first.
5. **Child Pipeline References** — `FlowPipelineExecute(pipeline="path")` for child pipelines.
6. **Reader Snap Connections** — `BinaryFileReader` output is binary; connect to parser first.
7. **Expression Library Restrictions** — Arrow functions only, no `function` keyword. Never use a reserved word as a bare object key or a parameter name, anywhere in an expression or `.expr` file (including objects returned by functions): `instanceof`, `typeof`, `in`, `matches`, `match`, `if`, `true`, `false`, `new`, `null`, `NaN`, `Infinity`. The platform reads it as the keyword and the import fails. Quote the key instead (`"match": ...`); `x.match` still reads it. `function` is fine as a key. Names that only contain a keyword (`matchPostcodeOnLine`) and method calls (`.match()`) are fine.
8. **TransformGroupByFields Output** — Always produces `group_by` array wrapper.
9. **Reader/Writer Param Names Differ** — `BinaryFileReader` takes `file_path`; `BinaryFileWriter` takes `filename` (+ `file_action`). Never copy reader params onto a writer.
10. **Never Guess — Consult Tools** — Always call `pygen_validate_snap_names(do_get_parameters=True)` for exact parameter names, types, and Expr()-eligibility. Call `pygen_get_snap_documentation` for behavior you're unsure about. There are 1,200+ snaps — tools are the source of truth.
11. **Lookup/Select/Execute Nest the Input** — These snaps emit their own output fields at the document root and put the ENTIRE input document under `original`. Downstream references to upstream fields must be `$original.<field>`; only the snap's declared output fields stay at the root. On Lookup snaps this is unconditional — `pass_through` governs no-match routing, not the nesting.
12. **Name What the Canvas Shows** — the canvas draws a label on two lines of ≤ 12 characters and cuts the rest. Use two words of ≤ 12 characters each, naming the step, not the snap type:

    | label | canvas shows |
    |---|---|
    | `Deduplicated Transactions` | `Deduplicated` / `Transactions` ✅ |
    | `Transform Customer Data` | `Transform` / `Customer ...` ❌ |
    | `Mapper` | names the snap, not the step ❌ |

    Every branch of a snap with 2+ non-error output views gets a `src_view_label` of one word, ≤ 8 characters (`Archive`, not `Aggregate` — the next snap covers the rest; shorten the user's terms: `in_transit` → `Transit`) — copy too, not just routers. If the snap has an `output_view_name` parameter (routers, `TransformDiff`), the label must equal it, so that name gets the same budget. On refine, rename only what the request touches. Details: Rule 12.
13. **Fields That May Be Absent** — Referencing a field the document lacks does not give null — the expression fails, even inside `$x != null ? … : …`. Read anything optional — an optional tool argument, an optional input field — with `$.get('x')` or `$.get('x', default)`.

## 6. SLPy Format Reference

**Read these reference files for complete SLPy format details:**

- `references/slpy_language_and_pipeline.md` — SLPy language constraints, pipeline architecture, parameters
- `references/connections_and_error_pipeline.md` — Error pipeline configuration, connection syntax & patterns, generation rules

Key constraints (read references for full details):
- SLPy is declarative — only imports, assignments, and `p.connect()` calls allowed
- No control flow (`if`/`for`/`while`), no functions, no print statements
- All snap imports must use: `from slpy.modules.Snap.<SnapName> import <SnapName>`
- Pipeline import: `from slpy.modules.Pipeline.Pipeline import Pipeline`
- Connections use `p.connect(src=, dst=, src_view_id=, dst_view_id=, src_output_type=, dst_input_type=)`

---

## Reference Documentation (On-Demand)

The following reference sections are available in the `references/` directory. **Read these files on-demand** using the Read tool when you need detailed information for the current pipeline. Do NOT read all files upfront — only load what the pipeline requires.

| File | Contents | When to Read |
|------|----------|--------------|
| `references/programming_model.md` | Foundational SnapLogic primer: snaps, pipelines, data types, connection semantics | Foundational read — when unfamiliar with SnapLogic concepts or onboarding |
| `references/critical_rules.md` | Critical generation rules: Expr() wrapping, type compatibility, HTTP/REST, Script Snap, child pipelines, reader connections, expression libraries, GroupByFields output, reader/writer params, Lookup/Select/Execute `$original` nesting, snap and output-view naming | Before generating any pipeline — study rules to prevent 90% of errors |
| `references/validation_checkpoints.md` | Full checkpoint details with code examples for all 10 checkpoints (1, 1.5, 2, 3, 4, 4b, 5, 5b, 6, 7) | When you need detailed examples for validation steps |
| `references/mcp_tool_reference.md` | Detailed pygen MCP tool usage patterns, examples, and best practices | When unsure how to use a specific pygen tool |
| `references/slpy_language_and_pipeline.md` | SLPy language constraints, pipeline architecture, parameters (§6.1–6.3) | When writing pipeline structure, params, or expression libraries |
| `references/connections_and_error_pipeline.md` | Error pipeline config, connection syntax & patterns, generation rules (§6.4–6.6) | When configuring connections or error handling |
| `references/accounts.md` | Finding workspace accounts from .slf, matching ref_class_id, emitting Account(...) with all 4 fields, graceful fallback | When a snap needs authentication (`pm_account`) — HTTP Client, database, SaaS |
| `references/snap_reference.md` | Snap categories, configurations, binary vs document flow, ELT pack isolation, Script Snap, document re-rooting snaps | When you need snap I/O types or configuration patterns |
| `references/expression_language.md` | Operators, JSONPath, functions (String/Number/Date/Array/Object/JSON/Base64/Digest/GZip/iconv/HTML), pipeline/task/SL functions, match operator | When writing complex expressions |
| `references/expression_libraries.md` | .expr file syntax restrictions, arrow function rules, library overlays, examples | When generating .expr expression library files |
| `references/generation_templates.md` | Complete pipeline structure template, .expr template, validation checklist | When generating a new pipeline from scratch |
| `references/expression_gotchas.md` | 12 critical gotchas for expression evaluation | When expressions produce unexpected null values or errors |
| `references/anti_patterns.md` | 22 common mistakes (0–21) with WRONG/CORRECT examples | When validating generated code or debugging errors |
| `references/troubleshooting.md` | Debugging workflows, silent failure patterns, execution errors, translate vs execute comparison | When slpy translate or execute fails |
| `references/cdc_patterns.md` | Change Data Capture implementation patterns for SLPy pipelines (hash-based CDC) | Specialized patterns — when building CDC or delta-detection pipelines |

### Quick Decision Guide

- **Simple pipeline** (read/transform/write with basic snaps): Sections 1-6 above are sufficient
- **Expression-heavy pipeline**: Read `expression_language.md` and `expression_gotchas.md`
- **Pipeline with .expr library**: Read `expression_libraries.md`
- **First pipeline of a session**: Read `generation_templates.md` for the structural template
- **Validation failures**: Read `troubleshooting.md` and `anti_patterns.md`
- **Unfamiliar snap**: Read `snap_reference.md`
- **CDC or delta-detection pipeline**: Read `cdc_patterns.md`
- **Request matches a row in Pipeline Patterns (below)**: Read that pattern's SKILL.md FIRST — it's a multi-pipeline bundle, not a single pipeline
- **Unfamiliar with SnapLogic concepts**: Read `programming_model.md`

## Pipeline Patterns

Some requests are not one pipeline but a fixed-format **bundle** of pipelines. Each row
is a sibling skill describing one such pattern. Before choosing how to generate and before
writing any code, scan this table: if the request asks for what a row describes, **Read
that pattern's SKILL.md first** and follow it -- the topology is boilerplate to copy, not
to derive from memory. If more than one row matches, read only the most specific one. If
no row applies, this skill alone is sufficient.

| Pattern | What it is, and when it applies | Read first |
|---|---|---|
| `agent-pipelines` | An AgentCreator agent or AI assistant (a driver pipeline plus its tool pipelines), or a tool pipeline for one. Not for MCP servers. | `../agent-pipelines/SKILL.md` |
| `mcp-server-pipelines` | An MCP server, or pipelines exposed as tools over MCP. | `../mcp-server-pipelines/SKILL.md` |
