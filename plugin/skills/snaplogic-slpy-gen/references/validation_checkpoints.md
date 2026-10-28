## 4. Validation Checkpoints

Follow these checkpoints (1–7, with sub-checkpoints 1.5, 4b, 5b) sequentially. Checkpoints 1-6 are for syntax and structure validation. Checkpoint 7 (execution) is OPTIONAL but the strongest quality lever — recommended whenever the pipeline has real transform/expression logic (build a test segment when source/sink snaps are unsupported or make live calls); skip pure pass-through and trivial pipelines the translator already covers. Keep fixing+re-running while exec surfaces new runtime bugs; stop when it passes or stalls; delete scratch/test `.py` files before finishing.

### Checkpoint 1: Snap Name Resolution (MANDATORY)

**When:** Before any code generation
**Tool:** `pygen_validate_snap_names(do_get_parameters=True)` — ONE batched call for ALL candidates.
**Required:** YES - Never skip this step

**Process:**
```python
# 1. Extract all snap names from requirements
snap_names = [
    "BinaryFileReader",      # From input specification
    "TransformCSVParser",       # For CSV parsing
    "TransformMapper",       # For transformations
    "TransformJSONFormatter", # For JSON output
    "BinaryFileWriter"       # For file writing
]
# 2. Validate with pygen — parameters come back in the same call
validated = mcp__snaplogic__pygen_validate_snap_names(
    snap_names=snap_names,
    do_get_parameters=True
)

# 3. Review the result
# - resolved: canonical names (typos corrected) + required params + account
#   requirements + IO types + exec support — usually everything needed to generate
# - unresolved: pick a different snap or use the listed near-candidates;
#   do NOT retry the same name
# - Parameters marked '(expr)' accept Expr(); all others take plain values
```

**What this prevents:**
- Invalid snap names causing runtime errors
- Typos in snap names
- Using deprecated or non-existent snaps
- Guessed parameter names (the #1 strict-translate error class)

### Checkpoint 1.5: Connection Validation

**When:** After snap name resolution, before detailed configuration
**Tool:** `pygen_validate_connections`
**Required:** REQUIRED for branching pipelines (router/join/union/copy); RECOMMENDED otherwise. Already settled during planning (Pattern P) — don't re-run it there.

**Process:**
```python
# 1. Write a skeleton SLPy with just snap declarations and p.connect() chains
skeleton = """
p = Pipeline(label="My Pipeline")
snap_0 = BinaryFileReader()
snap_1 = TransformCSVParser()
snap_2 = TransformMapper()
snap_3 = TransformJSONFormatter()
snap_4 = BinaryFileWriter()
p.connect([snap_0, snap_1, snap_2, snap_3, snap_4])
"""

# 2. Validate skeleton with pygen
result = mcp__snaplogic__pygen_validate_connections(skeleton_slpy=skeleton)

# 3. Review results
# - status: "valid" or "invalid"
# - errors: Type mismatches, invalid snap names
# - snap_io: IO metadata for all snaps (use for connection types)
# - warnings: Isolated snaps not in any connection, plus informational notes about open
#   views slpy assigned to meet a snap's minimum (output: fine unless a destination was
#   intended; input: a leg is unwired — connect it or confirm it is meant to be open)
```

**What this prevents:**
- Type mismatches between snaps (document→binary errors)
- Incorrect connection topology
- Wasted time writing full configurations for an invalid pipeline structure

**Common bridge patterns for type mismatches:**
- `BinaryFileReader` (binary) → `TransformBinarytoDocument` (codec=`'BYTE_ARRAY'`) → Script/`TransformMapper` (document)
- `SOAPExecute` (document) → `TransformXMLFormatter` → `TransformXMLParser` (binary)
- `TransformMapper` (document) → `TransformDocumenttoBinary` → `BinaryFileWriter`/`APISuiteHTTPClient` (binary)

**TransformDocumenttoBinary params:** Only `codec` (`'BYTE_ARRAY'`, `'DECODE_BASE64'`, `'NONE'`) and `binary_header_props` (optional). Always reads `$content` — there is no `field=` or `data_path=` parameter.

### Checkpoint 2: Snap Documentation Review (Selective)

**When:** After validation, before detailed configuration
**Tool:** `pygen_get_snap_documentation` and `pygen_get_snap_parameters`
**Required:** YES — for **connectivity snaps** and for **document re-rooting snaps** (`*Lookup`, `*Select`, `*Execute`). Other transform/flow snap documentation is deferred.

#### Process: Connectivity Snaps (Eager)

```python
# 1. Identify connectivity snaps from your candidate list
# Example candidate snaps: BinaryFileReader, TransformCSVParser, TransformMapper, APISuiteHTTPClient, SnowflakeBulkLoad
# Connectivity snaps: APISuiteHTTPClient, SnowflakeBulkLoad

# 2. Get documentation for connectivity snaps ONLY
docs = mcp__snaplogic__pygen_get_snap_documentation(
    snap_names=["APISuiteHTTPClient", "SnowflakeBulkLoad"]
)

# 3. Get parameters for connectivity snaps ONLY
params = mcp__snaplogic__pygen_get_snap_parameters(
    snap_names=["APISuiteHTTPClient", "SnowflakeBulkLoad"]
)
```

#### Process: Document Re-Rooting Snaps (Eager — MANDATORY)

Any snap whose name ends in `Lookup`, `Select`, or `Execute` may nest the entire input document under an `original` key, moving every upstream field down one level (see Rule 11 in `references/critical_rules.md`). This is not visible in the snap's parameter list, and `slpy translate` only catches a subset (it is silent after an `*Execute`, when `output_fields` is omitted, and past Snaps it cannot follow), so it must be settled before you write the downstream snap.

```python
# Fetch docs for every re-rooting snap in the pipeline, alongside the connectivity ones
docs = mcp__snaplogic__pygen_get_snap_documentation(
    snap_names=["SQLServerLookup", "OracleSelect"]
)
# In the output view description, look for the phrase: under the "original" key
```

Then, before writing the snap that consumes the lookup's output, list its fields in two groups:

| Group | Where it lives | Example |
|---|---|---|
| The re-rooting snap's declared `output_fields` | document root | `Expr("$ProductKey")` |
| Everything carried from upstream | under `original` | `Expr("$original.Id")` |

Apply the same split to `FlowRouter` conditions, `FlowFilter` expressions, and writer `updateCondition`s — not just Mappers.

#### Process: Other Transform/Flow Snaps (Deferred)

For the remaining transform and flow snaps (Mapper, Filter, Router, GroupBy, file readers/writers, parsers/formatters):
- Use the skill's reference sections and pygen pipeline examples
- Do NOT call `pygen_get_snap_documentation` or `pygen_get_snap_parameters` for these snaps during initial generation
- If `slpy translate` (Checkpoint 5) or `slpy exec` (Checkpoint 7) produces errors related to a transform/flow snap, **then** fetch that snap's documentation and parameters reactively to resolve the issue

### Checkpoint 3: Script Snap Review (If Present)

**When:** Pipeline specification includes Script Snap
**Required:** YES - Document justification

**Process:**
1. **Verify justification exists** - Check requirements for why Script Snap is needed
2. **List alternatives considered:**
   - TransformMapper for transformations?
   - Expression Library for complex logic?
   - Native snaps for integration?
   - APISuiteHTTPClient for API calls?
3. **Document in pipeline header** (see Script Snap section in §7)
4. **Add warning comment before Script Snap instantiation**

### Checkpoint 4: Child Pipeline Validation (If FlowPipelineExecute)

**When:** Pipeline uses FlowPipelineExecute to call child pipelines
**Required:** YES - Enforce literal names

**Process:**
1. **Identify FlowPipelineExecute snaps** in requirements
2. **Verify pipeline name is literal** (not expression):
   - ✅ `pipeline="ST001_INSPECTIONS"` - Literal string
   - ❌ `pipeline=Expr("_pipeline_path")` - Expression (avoid unless truly dynamic)
3. **Check against job_structure_index.json** (if available) for correct names
4. **Ensure params use Expr() for VALUES** (not pipeline name):

```python
# ✅ CORRECT
snap_2 = FlowPipelineExecute(
    label="Run Child Pipe",
    pipeline="ST001_INSPECTIONS",  # Literal name (slpy-inliner can detect)
    params=[
        FlowPipelineExecute.ParamsItem(
            param_name="FileName",
            param_value=Expr("_DeltaFileName")  # Expr OK for param VALUE
        ),
        FlowPipelineExecute.ParamsItem(
            param_name="ProcessDate",
            param_value=Expr("$run_date_DTS")  # Expr OK for param VALUE
        )
    ]
)
```

### Checkpoint 4b: File Extension Check (MANDATORY before writing)

Before writing the generated SLPy code to a file, verify:
- [ ] Pipeline file uses `.py` extension (NOT `.slpy` — the CLI will reject `.slpy`)
- [ ] Output destination will use `.slp` extension (NOT `.json`)

### Checkpoint 5: SLPy Translation and Validation via Bash (MANDATORY)

**Before running slpy translate, verify:**
- Source file has `.py` extension (not `.slpy`, not `.json`)
- Destination file has `.slp` extension (not `.json`, not `.py`)

```bash
cd {pipeline_dir} && slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict -expr
```

A single `slpy translate` run reports ALL errors at once, grouped by snap — read the whole list and fix them in ONE pass instead of one error per round-trip.

**`WARNING` lines on stderr are not optional noise — read them.** `slpy translate` reports them through the logger, not on stdout, so they appear alongside the command's other stderr output and never in the `.slp`. Translation warnings do not stop the `.slp` from being written, so a pipeline can translate "successfully" and still be wrong. Treat these as blocking:

| Warning | What it means | Fix |
|---|---|---|
| `... reads $X at the document root, but its upstream <Snap> nests the input document under $original` | The downstream Snap reads upstream fields at the wrong root. On the platform they resolve to null, and a null-safe reader drops the column silently (Rule 11, Mistake 21). | Prefix every flagged field with `$original.` — leave the upstream Snap's own output fields at the root. Re-translate and confirm the warning is gone. |
| `link references <view>, which this Snap does not have` | A connection names a view the Snap does not expose, so it is dropped. | Correct the `src_view_id` / `dst_view_id` on the `p.connect(...)` call. |

Never report a pipeline as validated while a warning of either kind is still printed.

`NOTE` lines on stderr are informational, not blocking: `<snap> (<Snap>): below minimum output views, assigned 1 open output view (output0); connect it or confirm nothing is meant to consume this output` means slpy declared an open view so the Snap meets its minimum. An assigned **output** view is fine unless a destination was intended; an assigned **input** view means a leg is unwired — connect it or confirm the input is meant to be open. Mention it to the user; do not invent a destination to silence it.

**Under `-strict` every reported error is fatal.** slpy raises `Strict mode: N error(s) … Pipeline was not generated` and writes **no `.slp`**, so there is no such thing as a warning you can leave behind. "Cosmetic" describes how cheap the fix is, never whether you can skip it:

**FIX and re-translate — all of these:**
- Invalid snap name (`not found in catalog`) → first confirm you didn't just omit `--schema-path` for a custom snap; otherwise re-validate the name with pygen
- Missing Expr() wrapper / invalid expression → add `Expr()` for `$`, `_`, or functions; fix the expression
- Type mismatch → check connection types, add a formatter/parser
- **Wrong parameter name** (`invalid value for 'file_path' … expected one of: 'filename', …`) → the error lists the valid names; use the right one, or drop the kwarg if it isn't needed. Cheap to fix, but fatal if left.
- **Invalid enum value** (`expected one of: 'OVERWRITE', 'APPEND', …`) → use an exact listed value.

**Genuinely no-op (nothing to fix):** a wrong-*case* enum value (`"overwrite"` for `OVERWRITE`) is case-folded silently and does not appear as an error at all.

**Loop discipline:** fix everything the run reported, then re-translate — normally ONE extra round, not one per error. If the same errors survive **2 rounds** and you can't resolve them, stop editing and say plainly, in user vocabulary, which step could not be configured and why. Your local strict translate wrote no `.slp`, so nothing was written and there is nothing to import — say plainly that the pipeline could not be produced and which step could not be configured. Never imply it was delivered. Never silently delete a parameter the user asked for (batch size, timeout, write mode, file name); look up its real name instead.

**Deferred documentation retrieval for transform/flow snaps:**
If `slpy translate` fails with a snap configuration error on a transform or flow snap, fetch that snap's documentation and parameters reactively:
```python
docs = mcp__snaplogic__pygen_get_snap_documentation(snap_names=["TransformMapper"])
params = mcp__snaplogic__pygen_get_snap_parameters(snap_names=["TransformMapper"])
```
Then fix the configuration and re-run `slpy translate`.

### Checkpoint 5b: Expression Library Integration (If .expr file generated)

**When:** After generating both .expr file and pipeline
**Required:** YES - Mandatory when expression library is generated

**Verification Steps:**
1. **Import exists** - Verify `ExpressionLibraries` import is present in pipeline
2. **Library configured** - Verify `p.expression_libraries = ExpressionLibraries(...)` is set
3. **Functions called** - Verify pipeline uses `lib.helpers.*` calls instead of duplicating logic
4. **No duplicate logic** - Search for inline implementations of library functions and replace with `lib.*` calls

**Checklist:**
- [ ] `from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries` is imported
- [ ] `p.expression_libraries = ExpressionLibraries(expression_library=[...])` is configured after Pipeline initialization
- [ ] All functions documented in docstring are actually called via `lib.helpers.*`
- [ ] No inline Expr() duplicates logic that exists in the .expr file

### Checkpoint 6: Expression Library Validation (If .expr file generated/modified)

**When:** After generating or modifying any expression library (.expr) file
**Tool:** slpy CLI `validate-expression` command via Bash
**Required:** YES - Mandatory for all .expr files

**Command format:**
```bash
slpy validate-expression -expr-lib {library_name}.expr
```

**Validation Loop:**
1. Run `slpy validate-expression -expr-lib {file}.expr`
2. If errors found:
   - Read error message (includes line number)
   - Fix the specific syntax issue
   - Re-run validation
3. Repeat until validation passes (no output = success)

### Checkpoint 7: Execution Validation (OPTIONAL — recommended for real transform logic)

**When:** After successful `slpy translate` (Checkpoint 5) and expression library validation (Checkpoint 6 if applicable)
**Tool:** slpy CLI `exec` command via Bash
**Required:** No — optional, but recommended whenever the pipeline has real transform/expression logic and its snaps are execution-supported

This checkpoint validates **runtime behavior**: actual data flow, transformation logic, and output correctness — catching things static validation can't (null references, wrong field mappings, bad aggregation logic, expression-library failures). It's optional but the single biggest lever on generated-pipeline reliability, so **reach for it whenever the pipeline does real transform/expression work**; skip it when there's nothing to exercise (pure pass-through, or a trivial pipeline the translator already fully validated). It is NOT a pass/fail gate — a zero exit code does not prove correctness (some runtime failures resolve to null instead of raising). Run as long as you're making progress: keep fixing+re-running while each exec surfaces a NEW concrete runtime bug (a multi-bug transform chain legitimately needs several passes), and stop when exec passes, an error repeats, or only cosmetic issues remain (Step 4).

#### Step 1: Determine Execution Feasibility

First decide whether exec adds signal (real transform logic → yes; pure pass-through / trivial → skip), then check snap support with `slpy exec --list-snaps`.

| Scenario | Action |
|----------|--------|
| **Real transform logic, all snaps execution-supported** | Run `slpy exec` directly (Step 4) |
| **Real transform logic, source/sink unsupported (Salesforce/Snowflake/DB) or live-call (`APISuiteHTTPClient`)** | Build a test segment (Step 3): replace the source with a `TransformJSONGenerator` (inline sample data — preferred) and any unsupported sink with `TransformJSONFormatter` + `BinaryFileWriter`, transforms identical, then exec it — keeps the run offline and reproducible |
| **Pure pass-through, or trivial pipeline the translator already validated** | Skip execution |
| **Pure binary read→write passthrough (no parser/formatter/transform)** | Skip execution — nothing to exercise; translate already validated it |

**Expression libraries:** Pipelines using `p.expression_libraries` with `lib.*` calls are fully supported. Library `.expr` files are loaded at build time and functions are available during expression evaluation. Use `--dry-run` to confirm libraries loaded successfully.

#### Step 2: Prepare Test Data

**Default: embed the sample data inline in a `TransformJSONGenerator`** — no separate file, so nothing to path-match or clean up:

```python
src = TransformJSONGenerator(
    editable_content='[{"currency":"USD","rate":1.08},{"currency":"GBP","rate":0.85}]',
    array_elements_as_documents=True,   # emit each array element as its own document
)
```
Pass `editable_content` as a **JSON-string literal** (not `json.dumps(...)` — the agent isn't executing Python at SLPy-eval time). Use 5-20 records matching the schema the FIRST transform expects.

**Avoid `$` inside the sample VALUES.** `editable_content` is evaluated as a Velocity template, so `"$id-100"` is rewritten to `{{ document.id }}-100` and renders as `-100` at exec time — your sample data silently loses content and the transform under test sees the wrong input. `$` followed by a non-identifier (`"$5.00"`, `"$.store.book"`) is left alone, but the safe habit is to keep `$word` out of sample values entirely (write `"USD 5.00"`, or `"id-100"`).

Only if you fell back to `BinaryFileReader` (binary/CSV input needed): write the sample file first (e.g. `.jsonl`, one JSON object per line, works with `TransformJSONParser(json_lines=True)`), and set the reader's `file_path` (NOT `filename`) to it.

#### Step 3: Create Test Segment Pipeline (when a source/sink snap can't execute locally or makes a live call)

When the pipeline's source/sink snaps aren't execution-supported (Salesforce, Snowflake, DB, etc.) or make a live external call (`APISuiteHTTPClient`), build a test segment so you can still exec the pipeline offline and reproducibly. Create a separate `{name}_test.py` file that replaces those source/sink snaps while keeping **all transformation snaps identical** to the production pipeline. Only skip the test segment when there's nothing between the endpoints to exercise (a pure binary passthrough).

**Prefer `TransformJSONGenerator` for the source** — it carries the sample data inline (`editable_content`), so there's no separate data file to write and no `file_path` param to get wrong (a common cause of "reader emits 0 docs" churn). Reach for `BinaryFileReader` + a written sample file ONLY when the transform chain genuinely needs binary or CSV input that JSONGenerator can't provide.

**Replacement Pattern Table:**

| Non-Executable Snap | Replacement (preferred first) | Notes |
|---------------------|-------------------|-------|
| Any document-emitting source (Salesforce, Snowflake, DB, `APISuiteHTTPClient`, REST) | `TransformJSONGenerator(editable_content='[{...},{...}]', array_elements_as_documents=True)` | Inline sample docs — **no data file, no `file_path`**. This is the default; it emits documents directly into the transform chain. |
| Source that MUST feed binary/CSV downstream | `BinaryFileReader(file_path='sample.csv')` + parser (`TransformCSVParser`/`TransformJSONParser`) | Only when the next snap needs a binary stream. Write the sample file first; the param is `file_path`, not `filename`. |
| Database/SaaS/cloud writers (Salesforce, Snowflake, S3, etc.) | `TransformJSONFormatter` + `BinaryFileWriter` | Write output to a JSON file for verification |

**CRITICAL RULE:** Transformation snaps (Mapper, Filter, Router, Aggregate, Join, Splitter, etc.) MUST be identical between the production pipeline and the test segment. Only source and sink snaps should differ.

**CRITICAL RULE:** When generating test assertion mappers that compute individual checks then derive a summary, split into sequential mappers. A single mapper cannot reference fields it computes (see Gotcha 12).

#### Step 4: Execute the Pipeline

**Run while making progress, not a fixed count.** Keep fixing+re-running while each exec surfaces a NEW concrete runtime bug you can fix — a multi-bug transform chain (e.g. wrong JSONPath → mapper drops all docs → fix → next field bug) legitimately needs several passes, and that's exactly where exec earns its keep. STOP when exec passes cleanly, the same error repeats (not converging), or only cosmetic issues remain. A green exec doesn't prove correctness, so don't re-run just to re-confirm. Use `--verbose` to inspect per-snap I/O. **Clean up:** a scratch/debug pipeline for diagnosis is fine, but `rm` it (and any test segment) before finishing.

```bash
# Direct execution (all snaps supported)
slpy exec {name}.py

# Test segment execution
slpy exec {name}_test.py

# With pipeline parameters (-e flag, no underscore prefix)
slpy exec {name}.py -e input_path=/data/test.jsonl -e batch_size=100

# With verbose output (recommended for debugging)
slpy exec {name}.py --verbose
```

#### Step 5: Verify Output

After successful execution, verify the output:

1. **File exists** — check that the output file was created
2. **Correct structure** — verify JSON/CSV structure matches expected schema
3. **Correct values** — spot-check computed values (aggregations, transformations, calculations)
4. **Correct count** — verify record count matches expectations (e.g., one output per group)
5. **Edge cases** — check handling of nulls, empty strings, missing fields
6. **Library function results** — if the pipeline uses `lib.*` calls, verify output values match expected library function behavior

#### Step 6: Handle Execution Errors

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| Unsupported snap type | Snap not in `slpy exec --list-snaps` | Create test segment with file I/O replacement |
| File not found | Test data file missing or wrong path | Create test data file or fix path |
| Null reference | Missing field in test data or upstream null | Add null-safe access, fix test data schema |
| Parameter not defined | Missing `-e` flag for pipeline parameter | Add `-e param=value` to exec command |
| Wrong output values | Transformation logic error | Debug expressions, check field references |
| Expression library file not found | `.expr` file missing or wrong path | Verify `.expr` file exists relative to pipeline file directory |
| Undefined library path: lib.X.Y | Library not declared in `p.expression_libraries` or alias mismatch | Check `as_` alias in `ExpressionLibraryItem` matches `lib.<alias>` usage in expressions |
