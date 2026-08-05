---
name: snaplogic-slpy-gen
description: "Generate SnapLogic SLPy pipelines and expression libraries. Uses pygen MCP tools for snap discovery/validation, then compiles with slpy translate -strict via Bash."
tools: Read, Write, Bash, TodoWrite, Glob, Grep, mcp__snaplogic__pygen_query_pipeline_examples, mcp__snaplogic__pygen_query_snap_examples, mcp__snaplogic__pygen_validate_snap_names, mcp__snaplogic__pygen_get_snap_parameters, mcp__snaplogic__pygen_get_snap_documentation, mcp__snaplogic__pygen_validate_connections, mcp__snaplogic__pygen_list_snaps_by_category, mcp__snaplogic__pygen_get_snap_io_info, mcp__snaplogic__pygen_get_all_snap_names
---

# SnapLogic SLPy Pipeline Generator

## 1. Overview

Generate production-ready SnapLogic pipelines in Python format (SLPy) and expression libraries (.expr) with comprehensive snap discovery, validation, and reference documentation.

SLPy is a **declarative format** (not executable Python) that must be converted to SLP JSON using the slpy CLI for import into SnapLogic. This skill automates the entire generation and validation workflow using pygen MCP tools.

Beyond static validation, SLPy pipelines can also be **executed locally** using the `slpy execute` command against a subset of supported snaps. This enables runtime validation of data flow and transformation logic without deploying to the SnapLogic platform. For pipelines that use non-supported snaps (e.g., Salesforce, Snowflake), a **test segment pipeline** can be created that replaces those snaps with local file readers/writers while keeping all transformation logic identical.

### File Naming Rules

SLPy pipeline files MUST use the `.py` extension. The slpy CLI rejects all other extensions.

- **SLPy source files**: `{name}.py` (e.g., `countries_analysis.py`) — NOT `.slpy`, NOT `.slpy.py`
- **SLP output files**: `{name}.slp` (e.g., `countries_analysis.slp`) — NOT `.json`, NOT `.pipeline`
- **Expression libraries**: `{name}.expr` (e.g., `helpers.expr`)

The `.slp` file IS JSON (SnapLogic's native pipeline format). Do not use `.json` — always use `.slp`.

### When to Use This Skill

This skill auto-triggers when requests involve:
- SnapLogic pipeline generation or creation
- SLPy (.py) or expression library (.expr) file generation
- Snap configuration and validation
- SnapLogic integration requirements
- Pipeline architecture or data flow design

## 2. Validation & Execution Commands

### slpy translate (MANDATORY)

After generating SLPy code, you MUST validate and translate using the Bash tool:
```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict
```

**MANDATORY: The `-strict` flag is ALWAYS required.** Strict mode halts translation on unsupported formats instead of silently warning and continuing. This ensures the generated `.slp` file is fully valid — silent warnings can produce pipelines that fail at runtime on the SnapLogic platform.

**Recommended: Add `-expr` to validate expressions during translation (catches expression syntax errors early):**
```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict -expr
```

**The `-src` and `-dest` flags are REQUIRED named arguments — do NOT pass the filename as a positional argument.**

**Custom snaps: `--schema-path <path>` is MANDATORY whenever the pipeline uses custom snaps.**

**Guard:** If neither `## Custom Snap Definitions` nor `## Translation` appears in the user request, ignore this section entirely — do not attempt to introduce custom snaps.

Signal: the user request contains a `## Custom Snap Definitions` and `## Translation` section with a specific schema path. In that case, every `slpy translate` invocation (including retries after fixes) MUST pass `--schema-path`:

```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict -expr --schema-path {schema_path_from_request}
```

Without this flag, strict mode rejects custom snaps with `snap name '...' not found in catalog`. If you see that error on a snap defined in `## Custom Snap Definitions`, you forgot `--schema-path`, not the snap name — re-run with the flag instead of "fixing" the name.

**Round-trip edits: `--preserve-ids <original.slp>` is MANDATORY when the `.py` descends from an existing platform pipeline** (the user provided a platform-exported `.slp` that was translated to `.py`, or you are refining such a `.py`):

```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict --preserve-ids {original}.slp
```

Without the flag, translate mints fresh UUIDs for every snap — on re-import the platform sees a brand-new set of snaps instead of an edit, dropping all existing links and snap identity. With it, kept snaps retain their original UUIDs and canvas positions, new snaps get fresh UUIDs placed next to their neighbors, and removed snaps are dropped. Success prints a summary: `preserve-ids: 5 snap UUID(s) preserved, 1 fresh`.

- **Do not rename `snap_N` variables when editing an encoded `.py`** — the variable name is the join key back to the original snaps; renaming reads as delete + add and loses that snap's identity.
- The flag only applies to the `.py` → `.slp` direction, and composes with `-strict`, `-expr`, and `--schema-path`.
- Keep the original `.slp` export unmodified; pass the same file on every re-translate in the session.

Example (file in current directory):
```bash
slpy translate -src countries_by_continent.py -dest countries_by_continent.slp -strict
```

Example (file in subdirectory):
```bash
slpy translate -src countries/countries_by_continent.py -dest countries/countries_by_continent.slp -strict
```

**Expected success output** No output and the .slp file is created.

**Expected error output:**
```
Error: Line 42: Invalid snap name 'BadSnapName'
```

If you see `slpy: error: unrecognized arguments:` — you forgot the `-src` flag.

**Why slpy CLI translate:**
- Official SnapLogic tool for validation AND translation
- Generates .slp files (native SnapLogic JSON format for platform upload)
- Single command for validation + deployment artifact
- More comprehensive validation than MCP alternatives

### slpy validate-expression (for .expr files)

```bash
slpy validate-expression -expr-lib {library_name}.expr
```

This validates expression library syntax separately from pipeline translation. Use this when generating or modifying `.expr` files to catch syntax errors before pipeline validation.

### slpy execute (OPTIONAL — Recommended When Feasible)

```bash
# Basic execution
slpy exec {pipeline_name}.py

# With pipeline parameters (no underscore prefix in -e flag)
slpy exec {pipeline_name}.py -e param_name=value -e another_param=value2

# Dry run (shows pipeline structure and loaded expression libraries)
slpy exec {pipeline_name}.py --dry-run

# Verbose output (recommended for debugging)
slpy exec {pipeline_name}.py --verbose
```

**What it does:**
- Runs the pipeline locally, processing actual data through each snap
- Performs real file I/O (reads/writes local files)
- Makes real HTTP calls for `APISuiteHTTPClient` snaps (use test data files instead to avoid external dependencies)
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
- `APISuiteHTTPClient` IS execution-supported but makes **real network calls** — replace with `BinaryFileReader` + test data for controlled testing
- No account or credential support (cannot authenticate to external systems)
- For pipelines with non-supported snaps, create a **test segment pipeline** replacing those snaps with file I/(see Checkpoint 7)

**IMPORTANT:** `slpy execute` is NOT a replacement for `slpy translate`. Both serve different purposes:
- `slpy translate` = syntax validation + .slp generation (MANDATORY)
- `slpy execute` = runtime validation of data flow (RECOMMENDED when feasible)

### Execution-Supported Snaps

The `slpy execute` command can run SLPy pipelines locally against a subset of supported snaps. To determine which snaps are currently supported:

```bash
slpy exec --list-snaps
```

This command returns the current list of execution-supported snaps. The list evolves over time as new snaps gain execution support, so **always run this command** rather than relying on a hardcoded list.

**How to use in the workflow:**
1. Run `slpy exec --list-snaps` to get the current supported snap list
2. Compare the pipeline's snaps against the supported list
3. If all snaps are supported → pipeline is fully executable
4. If some snaps are not supported → create a test segment pipeline replacing unsupported snaps with file I/O (see Checkpoint 7)

**Notable execution-supported snaps:** `Script` (runs Python scripts in a sandboxed environment — same ScriptHook API as the platform), `FlowPipelineExecute` (runs child `.py` pipelines locally). These do NOT require test segment workarounds.

**Key note:** `APISuiteHTTPClient` is execution-supported but makes **real network calls** — for testing purposes, replace with `BinaryFileReader` + test data file to avoid external dependencies and ensure reproducible test results.

### Pygen MCP Tools Used for Validation

**The only pygen MCP tools you should use:**
- `pygen_validate_snap_names` - For validating snap names BEFORE generation (Checkpoint 1)
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
2. `pygen_validate_snap_names([snaps], do_get_parameters=True)`
3. `pygen_get_snap_documentation([connectivity_snaps_only])`
4. Generate SLPy (file MUST have .py extension) → Validate with Bash: `slpy translate -src X.py -dest X.slp -strict`
5. If pipeline has transform/flow snaps: `slpy exec X.py` (or test segment if some snaps unsupported)

#### Pattern 1: Simple Pipeline (Target: 5-6 calls)
**Use for:** Standard ETL with known snaps
- Multi-step transformations
- Basic data quality checks
- Single source, single destination

**Workflow:**
1. `pygen_query_pipeline_examples("combined intent")`
2. `pygen_validate_snap_names([snaps], do_get_parameters=false)`
3. `pygen_validate_connections(skeleton_slpy)` — validate snap names + connection type compatibility
4. `pygen_get_snap_documentation([connectivity_snaps_only])`
5. `pygen_get_snap_parameters([connectivity_snaps_only])`
6. Generate SLPy (file MUST have .py extension) → Validate with Bash: `slpy translate -src X.py -dest X.slp -strict`
7. Execute: `slpy exec X.py` directly, or create test segment `X_test.py` if some snaps unsupported

#### Pattern 2: Complex Pipeline (Target: 6-8 calls)
**Use for:** Advanced integration scenarios
- Multi-stage transformations with routing
- Specialized integrations (Salesforce, SAP, NetSuite)
- Error handling and orchestration
- ELT patterns with database pushdown

**Workflow:**
1. `pygen_query_pipeline_examples("primary segment")`
2. `pygen_query_snap_examples("specialized integrations")` — or `pygen_list_snaps_by_category(pack="Snowflake")` if you know the target system but need to discover available snaps
3. `pygen_validate_snap_names([snaps], do_get_parameters=false)`
4. `pygen_validate_connections(skeleton_slpy)` — validate snap names + connection type compatibility
5. `pygen_get_snap_documentation([connectivity_snaps_only])`
6. `pygen_get_snap_parameters([connectivity_snaps_only])`
7. Generate SLPy (file MUST have .py extension) → Validate with Bash: `slpy translate -src X.py -dest X.slp -strict`
8. Execute: `slpy exec X.py`, or create test segment `X_test.py` replacing non-executable snaps with file I/O, then `slpy exec X_test.py`

#### Pattern 3: Refinement (Target: 1-3 calls)
**Use for:** Updating existing pipelines
- Modifying snap configurations
- Adding error handling
- Performance optimizations

**Workflow:**
1. Read existing .py file
2. If adding new snaps: `pygen_get_snap_documentation([new_connectivity_snaps])`
3. Apply modifications (file MUST have .py extension) → Validate with Bash: `slpy translate -src X.py -dest X.slp -strict`
4. If changes affect transformation logic: re-execute (`slpy exec X.py`) or update test segment and re-execute

**If the pipeline came from the platform** (a platform-exported `.slp` translated to `.py`), two extra rules apply to every refinement:
- Translate with `--preserve-ids original.slp` (see §2) so snap UUIDs, links, and canvas positions survive re-import — and keep the existing `snap_N` variable names.
- Preserve account bindings you didn't ask to change — in particular `pm_account=Expr('lib.env.*')` expression refs (see Rule 10).

### Tool Efficiency Rules

1. **Snap name validation is mandatory** - Always validate snap names using `pygen_validate_snap_names` before generation (this is different from final pipeline translation via slpy CLI)
2. **Documentation is selective** - Get snap documentation using `pygen_get_snap_documentation` for **connectivity snaps only** (Enterprise, database, cloud storage, HTTP). Transform and Flow snap documentation is deferred until needed (see Checkpoint 2).
3. **Maximum 8 MCP tool calls** - Generate with available information, iterate if needed
4. **No duplicate MCP calls** - Never call the same pygen tool with the same or overlapping query twice. If you need more examples, use a DIFFERENT query string, not a repeat.
5. **Use tool-provided schemas, not memory** - The `(expr)` marker in parameter schemas from `pygen_get_snap_parameters` tells you which params accept `Expr()`. Parameters without `(expr)` expect plain strings. Don't guess from memory — there are 900+ snaps.
6. **Tool call targets by pattern:**
   - Express Mode: 3 calls
   - Simple: 5-6 calls (includes skeleton validation)
   - Complex: 6-8 calls (includes skeleton validation + optional snap discovery)
   - Refinement: 1-3 calls

### Pygen MCP Tool Reference

#### pygen_query_pipeline_examples

**Purpose:** Find pipeline patterns and understand snap relationships

**When to use:**
- Understanding pipeline structure before generation
- Discovering how snaps connect in common patterns
- Learning typical ETL workflows

**Input strategy:**
- Break query into atomic concepts with detailed applications
- Include source system, transformation type, destination system
- Be specific about data formats (CSV, JSON, XML, Parquet, etc.)

**Example queries:**
- "Read CSV file from S3, parse with CSV parser, transform with mapper, format as JSON, write to Snowflake"
- "Query Salesforce with SOQL, filter records, aggregate data, write to PostgreSQL"
- "REST API call with HTTP client, parse JSON response, route based on status, error handling"

**Output:** Complete pipeline examples with snap connections and metadata

#### pygen_query_snap_examples

**Purpose:** Find specific snaps for specialized integrations

**When to use:**
- Need snaps for specific systems (Salesforce, NetSuite, SAP, etc.)
- Unclear which snap to use for a requirement
- Discovering available snaps for a technology

**Input strategy:**
- Detailed integration needs with application names
- Include action type (read, write, query, bulk load, etc.)
- Specify technology (SQL, NoSQL, cloud storage, SaaS application)

**Example queries:**
- "Snowflake bulk load for large dataset"
- "Salesforce SOQL query with filtering"
- "MongoDB aggregate pipeline operations"
- "S3 file reader with pattern matching"

**Output:** List of snap names with descriptions

#### pygen_validate_snap_names

**Purpose:** Validate snap names and optionally retrieve parameters

**When to use:** ALWAYS before generation (mandatory checkpoint)

**Input:** List of all snap names planned for the pipeline

**Options:**
- `do_get_parameters=true` - Get parameters in same call (efficient)
- `do_get_parameters=false` - Validation only (if getting docs separately)

**Important notes:**
- Returns corrected snap names if typos or variations found
- Parameters marked with `(expr)` are expression-enabled
- Not all `(expr)` parameters need Expr() wrapper - only use when necessary
- This is the FINAL validation before generation - NEVER skip

**Output:** Validated snap names, optional parameters/configurations

#### pygen_get_snap_documentation

**Purpose:** Retrieve detailed snap explanations with examples

**When to use — selective by snap category:**

- **Eagerly (before generation):** Connectivity snaps — databases (Snowflake, PostgreSQL, etc.), Enterprise SaaS (Salesforce, SAP, NetSuite, etc.), cloud storage (S3, Azure Blob, etc.), APISuiteHTTPClient. These snaps have complex, varied configuration not covered by the skill's static references.
- **Deferred (on error):** Transform and Flow snaps — only fetch if `slpy translate` or `slpy exec` produces errors related to these snaps. Transform/Flow snaps are well-documented in this skill reference.

**Why selective:**
- Connectivity snap documentation provides critical context for complex configuration (auth, connection params, query syntax, bulk modes)
- Transform/Flow snaps follow consistent patterns already covered by the skill's reference sections
- Fetching all documentation adds latency and consumes context window without significant benefit for well-known snaps

**Input:** List of validated snap names (connectivity snaps only for eager calls)

**Output:** Detailed text documentation with explanations

**BEST PRACTICE:** Call this BEFORE `pygen_get_snap_parameters` for connectivity snaps to understand behavior first, then get exact configuration fields.

#### pygen_get_snap_parameters

**Purpose:** Retrieve exact parameter names and types for snap configuration

**When to use:**
- After documentation (preferred sequence)
- For final configuration of snap instantiation
- Need exact field names and data types

**Input:** List of validated snap names

**Output:** SLPy code format configuration with parameter definitions

**Note:** Parameters alone don't explain behavior - get documentation first for full context.

#### pygen_validate_connections

**Purpose:** Validate pipeline structure (snap names + connection type compatibility) before full code generation

**When to use:**
- After determining pipeline structure (which snaps connect to which)
- Before writing full snap configurations
- To catch type mismatches (document→binary errors) and invalid snap names early

**Input:** Skeleton SLPy code with snap declarations and `p.connect()` chains (no configurations needed)

**Skeleton format:**
```python
p = Pipeline(label="My Pipeline")
snap_0 = BinaryFileReader()
snap_1 = TransformCSVParser()
snap_2 = TransformMapper()
p.connect([snap_0, snap_1, snap_2])
```

**Multi-branch skeleton:**
```python
p = Pipeline(label="My Pipeline")
snap_0 = FlowRouter()
snap_1 = TransformMapper()
snap_2 = BinaryFileWriter()
snap_3 = TransformMapper()
snap_4 = BinaryFileWriter()
p.connect([OPEN_VIEW.INPUT, snap_0, snap_1, snap_2])
p.connect([snap_0, snap_3, snap_4])
```

**Output:**
- `status`: "valid" or "invalid"
- `errors`: Type mismatches, invalid snap names with correction suggestions
- `snap_io`: IO metadata (input/output types) for all validated snaps
- `warnings`: Isolated snaps (declared but not connected)

**Key benefit:** Catches connection type mismatches (Rule 2) before you invest time writing full configurations. Also returns snap IO metadata that helps ensure correct `src_output_type`/`dst_input_type` in connections.

#### pygen_list_snaps_by_category

**Purpose:** Discover available snaps filtered by category and/or snap pack

**When to use:**
- Know the target system (e.g., "Snowflake") but unsure which specific snaps exist
- Need to find all read or write snaps for a particular integration
- Exploring what's available for a specific snap pack
- Complement to `pygen_query_snap_examples` when you want a complete list rather than vector-search results

**Parameters:**
- `category` (optional): One of: `read`, `write`, `transform`, `format`, `flow`, `parse`
- `pack` (optional): Snap pack name, e.g., "Snowflake", "Salesforce", "Binary", "Transform", "S3"

**Example calls:**
- All Snowflake snaps: `pygen_list_snaps_by_category(pack="Snowflake")`
- All read snaps: `pygen_list_snaps_by_category(category="read")`
- Snowflake write snaps: `pygen_list_snaps_by_category(category="write", pack="Snowflake")`

**Output:** List of matching snap names with their pack and category metadata, plus count

**Note:** This is a deterministic filter (not vector search) — it returns exact matches by category/pack. Use `pygen_query_snap_examples` for fuzzy/semantic search when you're unsure of the exact category or pack name.

#### pygen_get_snap_io_info

**Purpose:** Get snap I/O type metadata (input/output types for each view)

**When to use:**
- Planning connections between snaps
- Determining whether a snap outputs binary or document
- Resolving type mismatch errors

**Input:** List of snap names

**Output:** I/O metadata showing input/output view types for each snap

#### pygen_get_all_snap_names

**Purpose:** List all 830+ snap names in the catalog

**When to use:**
- When you need to search for a snap name but aren't sure of the category or pack
- Use sparingly — returns a long list that consumes context

**Output:** Complete list of all available snap names

#### slpy translate (via Bash tool)

**Purpose:** Validate and translate SLPy Python files to SLP JSON format

**When to use:** MANDATORY after generating SLPy code (Checkpoint 5)

**Command format:**
```bash
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict
```

**What it does:**
- Validates SLPy syntax (snap names, connections, expressions, parameters)
- Translates .py to .slp (native SnapLogic JSON pipeline format)
- Outputs deployment-ready pipeline files for platform upload
- Reports errors with line numbers for debugging

**CRITICAL:** This is the mandatory tool for final pipeline validation and .slp generation.

#### slpy execute (via Bash tool)

**Purpose:** Execute SLPy pipelines locally for runtime validation of data flow and transformation logic

**When to use:** RECOMMENDED after successful `slpy translate` (Checkpoint 7), when the pipeline uses execution-supported snaps

**IMPORTANT:** `slpy execute` is NOT a replacement for `slpy translate`. Both serve different purposes:
- `slpy translate` = syntax validation + .slp generation (MANDATORY)
- `slpy execute` = runtime validation of data flow (RECOMMENDED when feasible)

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

Follow these 7 checkpoints sequentially. Checkpoints 1-6 are for syntax and structure validation. Checkpoint 7 (execution validation) is optional but recommended when feasible.

### Checkpoint 1: Snap Name Validation (MANDATORY)

**When:** Before any code generation
**Tool:** `pygen_validate_snap_names` — **always** use `do_get_parameters=True` to get exact parameter names (prevents parameter guessing errors)
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

# 2. Validate with pygen
validated = mcp__snaplogic__pygen_validate_snap_names(
    snap_names=snap_names,
    do_get_parameters=True  # Get parameters in same call (efficient)
)

# 3. Review validated names and parameters
# - Check for any corrections (typos fixed)
# - Review expression-enabled parameters (marked with '(expr)')
# - Understand required vs optional parameters
```

**What this prevents:**
- Invalid snap names causing runtime errors
- Typos in snap names
- Using deprecated or non-existent snaps

### Checkpoint 1.5: Connection Validation (RECOMMENDED)

**When:** After snap name validation, before detailed configuration
**Tool:** `pygen_validate_connections`
**Required:** REQUIRED for all pipelines

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
# - warnings: Isolated snaps not in any connection
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
**Required:** YES — but only for **connectivity snaps**. Transform/Flow snap documentation is deferred.

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

#### Process: Transform/Flow Snaps (Deferred)

For transform and flow snaps (Mapper, Filter, Router, GroupBy, file readers/writers, parsers/formatters):
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
    label="Execute Child Pipeline",
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
slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict
```

**If errors occur:**
1. **Read error message carefully** - Includes line number and specific issue
2. **Identify error type:**
   - Invalid snap name → Re-validate with pygen
   - Missing Expr() wrapper → Add Expr() for $, _, or functions
   - Type mismatch → Check connection types, add formatter/parser
   - Invalid parameter → Check pygen snap parameters for correct field names
   - Syntax error → Review SLPy syntax in §6
3. **Fix SLPy code** - Apply correction based on error type
4. **Re-run slpy translate** - Validate fix
5. **Repeat until successful** - Zero errors required

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

### Checkpoint 7: Execution Validation (OPTIONAL — Recommended When Feasible)

**When:** After successful `slpy translate` (Checkpoint 5) and expression library validation (Checkpoint 6 if applicable)
**Tool:** slpy CLI `exec` command via Bash
**Required:** YES — when any transform/flow snaps are present

This checkpoint validates **runtime behavior**: actual data flow, transformation logic, and output correctness. It catches errors that static validation (`slpy translate`) cannot detect, such as null references, incorrect field mappings, wrong aggregation logic, and data type issues.

#### Step 1: Determine Execution Feasibility

Run `slpy exec --list-snaps` to get the current list of execution-supported snaps, then compare against the pipeline's snaps.

| Scenario | Action |
|----------|--------|
| **All snaps supported** | Pipeline is fully executable — proceed to Step 4 |
| **Some snaps not supported** | Create a test segment pipeline (Step 3) replacing unsupported snaps with file I/O |
| **No transform logic** (pure pass-through, only unsupported snaps) | Execution validation adds little value — skip |

**Expression libraries:** Pipelines using `p.expression_libraries` with `lib.*` calls are fully supported. Library `.expr` files are loaded at build time and functions are available during expression evaluation. Use `--dry-run` to confirm libraries loaded successfully.

#### Step 2: Prepare Test Data

If the pipeline reads from files or the test segment replaces source snaps with file readers, verify test data exists:

1. **Check if input files exist** — if the pipeline reads from a known file, verify it's present
2. **Create JSONL sample data if needed** — 5-20 records matching the expected input schema:

```jsonl
{"name": {"common": "Germany"}, "continents": ["Europe"], "population": 83240525}
{"name": {"common": "Brazil"}, "continents": ["South America"], "population": 212559417}
{"name": {"common": "Japan"}, "continents": ["Asia"], "population": 126476461}
```

**JSONL format** (one JSON object per line) is recommended because:
- Works directly with `TransformJSONParser` (set `json_lines=True`)
- Easy to create and edit
- Each line is independently valid JSON

#### Step 3: Create Test Segment Pipeline (If Needed)

When some snaps are not execution-supported, create a separate `{name}_test.py` file that replaces non-executable source/sink snaps with file I/O while keeping **all transformation snaps identical** to the production pipeline.

**Replacement Pattern Table:**

| Non-Executable Snap | Replacement Snaps | Notes |
|---------------------|-------------------|-------|
| Database/SaaS readers (Salesforce, Snowflake, etc.) | `BinaryFileReader` + `TransformJSONParser` | Read from JSONL test data file |
| Database/SaaS writers (Salesforce, Snowflake, etc.) | `TransformJSONFormatter` + `BinaryFileWriter` | Write output to JSON file for verification |
| `APISuiteHTTPClient` (as source) | `BinaryFileReader` + `TransformJSONParser` | Avoid real network calls during testing |
| Cloud storage readers (S3, Azure Blob) | `BinaryFileReader` | Read from local file instead |
| Cloud storage writers (S3, Azure Blob) | `BinaryFileWriter` | Write to local file instead |

**CRITICAL RULE:** Transformation snaps (Mapper, Filter, Router, Aggregate, Join, Splitter, etc.) MUST be identical between the production pipeline and the test segment. Only source and sink snaps should differ.

**CRITICAL RULE:** When generating test assertion mappers that compute individual checks then derive a summary, split into sequential mappers. A single mapper cannot reference fields it computes (see Gotcha 12).

#### Step 4: Execute the Pipeline

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

**Debugging tip:** When execution produces unexpected output, rerun with `--verbose` to inspect per-snap I/O rather than creating debug pipelines.

## 5. Critical Generation Rules

These 10 rules prevent 90% of SLPy generation errors. Study these carefully before generating any pipeline.

### Rule 1: Expr() Wrapper Decision (MOST COMMON ERROR)

The Expr() wrapper is required when a parameter value contains SnapLogic expressions that need runtime evaluation. Misusing Expr() is the #1 cause of validation failures.

**ALWAYS use Expr() when value contains:**

1. **Dollar sign `$`** - Document field references
   - `$field` - Top-level field
   - `$customer.name` - Nested field
   - `$items[0].price` - Array access
   - `$['field with spaces']` - Bracket notation

2. **Underscore prefix `_`** - Pipeline parameters
   - `_batchSize` - Parameter access
   - `_environment` - Configuration values
   - `_debug == 'true'` - Parameter comparison

3. **Functions** - Built-in or library functions
   - `'/data/' + _environment + '.csv'`
   - `Date.now()`
   - `parseInt($amount)`
   - `lib.dates.prev_month()`

4. **Operators with $ or _**
   - `$amount > 1000`
   - `_debug == 'true'`
   - `$state == 'CA' && $amount > 500`

**NEVER use Expr() for:**

1. **Plain string literals** - No special characters
   - `'customers.csv'`
   - `'output.json'`
   - `'/data/files/'`

2. **Numeric literals** - Direct numbers
   - `100`
   - `3.14`
   - `5000`

3. **Boolean values** - Python booleans
   - `True`
   - `False`

**Quick Check**: Does the string contain `$` or `_` as a prefix? → Use `Expr()`. Is it a plain literal? → Don't use `Expr()`.

**Examples - CORRECT:**

```python
# Document field reference - needs Expr()
snap_0 = FlowFilter(
    filter_expression=Expr("$state == 'CA'")  # $ requires Expr()
)

# Pipeline parameter - needs Expr()
snap_1 = BinaryFileReader(
    file_path=Expr("'/data/' + _environment + '/file.csv'")  # _ requires Expr()
)

# Function call - needs Expr()
snap_2 = TransformMapper(
    mapping={
        'timestamp': Expr("Date.now()")  # Function requires Expr()
    }
)

# Plain string literal - no Expr()
snap_3 = BinaryFileWriter(
    filename='output.json'  # No $ or _ or functions - plain string
)

# Numeric literal - no Expr()
snap_4 = FlowFilter(
    batch_size=1000  # Plain number - no Expr()
)
```

**Examples - INCORRECT:**

```python
# WRONG - Missing Expr() for $ reference
snap_0 = FlowFilter(
    filter_expression="$state == 'CA'"  # ERROR: $ without Expr()
)

# WRONG - Missing Expr() for _ parameter
snap_1 = BinaryFileReader(
    file_path="/data/" + _environment + "/file.csv"  # ERROR: Python concat invalid
)

# WRONG - Unnecessary Expr() for plain string
snap_2 = BinaryFileWriter(
    filename=Expr("'output.json'")  # ERROR: Unnecessary Expr() wrapper
)

# WRONG - Unnecessary Expr() for number
snap_3 = FlowFilter(
    batch_size=Expr("1000")  # ERROR: Unnecessary Expr() wrapper
)
```

**IMPORTANT: All SnapLogic JavaScript expressions must be provided as string values when populating Snap configuration parameters.** You cannot use arbitrary Python expressions to form a parameter value. Always wrap expressions in `Expr("...")`.

**String Literals Within Expressions:**
```python
# CORRECT - Strings enquoted inside Expr()
expression=Expr("'prefix_' + $name + '_suffix'")

# WRONG - Missing quotes around string literals
expression=Expr("prefix_ + $name + _suffix")
```

**Numeric Values Within Expr():**
```python
# WRONG - Creates string "1.5", not number 1.5
expression=Expr("'1.5'")

# CORRECT - Creates number 1.5
expression=Expr('1.5')
```

### Rule 2: Type Compatibility Matrix

SnapLogic enforces strict type compatibility between snap connections. Mismatched types cause validation errors and runtime failures.

**Type Compatibility Table:**

| Source Output | Destination Input | Compatible? | Solution |
|--------------|-------------------|-------------|----------|
| document     | document          | ✅ Yes      | Direct connection |
| document     | document+binary   | ✅ Yes      | Direct connection |
| document     | binary            | ❌ No       | Add **formatter** (JSON/CSV/XML) between |
| binary       | binary            | ✅ Yes      | Direct connection |
| binary       | document+binary   | ✅ Yes      | Direct connection |
| binary       | document          | ❌ No       | Add **parser** (JSON/CSV/XML) between |

**Data Type Definitions:**

- **document** - Structured JSON-like objects used by transformation snaps (Mapper, Filter, Router, Join, Aggregate)
- **binary** - Raw bytes used for files, media, and streaming (File Reader/Writer, S3 Reader/Writer). Note: `APISuiteHTTPClient` outputs **document** data by default — only produces binary when explicitly configured for file/binary download.

**Common Patterns:**

**Pattern: document → binary (File Write)**
```python
snap_0 = TransformMapper(...)  # Output type: document
snap_formatter = TransformJSONFormatter()  # Converts document → binary
snap_1 = BinaryFileWriter(...)  # Input type: binary
p.connect(src=snap_0, dst=snap_formatter)
p.connect(src=snap_formatter, dst=snap_1)
```

**Pattern: binary → document (File Read)**
```python
snap_0 = BinaryFileReader(...)  # Output type: binary
snap_parser = TransformCSVParser()  # Converts binary → document
snap_1 = TransformMapper(...)  # Input type: document
p.connect(src=snap_0, dst=snap_parser)
p.connect(src=snap_parser, dst=snap_1)
```

**Pattern: ETL Pipeline with Proper Type Flow**
```python
# READ (binary)
snap_0 = BinaryFileReader(label="Read CSV from S3", file_path="/data/input.csv")

# PARSE (binary → document)
snap_1 = TransformCSVParser(label="Parse CSV to Documents")
p.connect(src=snap_0, dst=snap_1, src_output_type="binary", dst_input_type="binary")

# TRANSFORM (document → document)
snap_2 = TransformMapper(label="Transform Data")
p.connect(src=snap_1, dst=snap_2, src_output_type="document", dst_input_type="document")

# FORMAT (document → binary)
snap_3 = TransformJSONFormatter(label="Format as JSON")
p.connect(src=snap_2, dst=snap_3, src_output_type="document", dst_input_type="document")

# WRITE (binary)
snap_4 = BinaryFileWriter(label="Write JSON to S3", filename="/data/output.json")
p.connect(src=snap_3, dst=snap_4, src_output_type="binary", dst_input_type="binary")
```

### Rule 3: HTTP/REST Operations

**PRIMARY DIRECTIVE:** ALWAYS use `APISuiteHTTPClient` for ALL HTTP/REST operations.

**FORBIDDEN - Legacy REST Snaps:**
- `RestGet`, `RestPost`, `RestPut`, `RestDelete`, `RestPatch` — NEVER generate these. Use `APISuiteHTTPClient` instead.

**Why APISuiteHTTPClient:**
- Modern authentication support (OAuth2, JWT, mTLS)
- Advanced retry logic with exponential backoff
- Connection pooling and performance optimization
- Better error handling and diagnostics
- Support for all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- Request/response transformations
- Cookie management
- Active maintenance (REST Snap Pack is legacy/deprecated)

**Migration from REST Snaps:**

| Legacy Snap | Replace With | Method Parameter |
|-------------|--------------|------------------|
| `RestGet` | `APISuiteHTTPClient` | `method='GET'` |
| `RestPost` | `APISuiteHTTPClient` | `method='POST'` |
| `RestPut` | `APISuiteHTTPClient` | `method='PUT'` |
| `RestDelete` | `APISuiteHTTPClient` | `method='DELETE'` |
| `RestPatch` | `APISuiteHTTPClient` | `method='PATCH'` |

**Prefer Document Output:**

`APISuiteHTTPClient` outputs **document** data by default for JSON/XML/text API responses. When using document output, **no Parser Snap is needed** after the HTTP Client — the response is already structured document data that can connect directly to Mapper, Filter, Router, and other transformation snaps.

Only use binary output entity when downloading raw files or binary content (e.g., images, PDFs, zip archives).

```python
# WRONG - Unnecessary parser after HTTP Client (document output is default)
snap_api = APISuiteHTTPClient(label="Call REST API", method="GET", url="https://api.example.com/data")
snap_parser = TransformJSONParser(label="Parse Response")  # UNNECESSARY
snap_mapper = TransformMapper(label="Transform Data", mappings=[...])
p.connect(src=snap_api, dst=snap_parser)
p.connect(src=snap_parser, dst=snap_mapper)

# CORRECT - Connect HTTP Client directly to transformation snaps
snap_api = APISuiteHTTPClient(label="Call REST API", method="GET", url="https://api.example.com/data")
snap_mapper = TransformMapper(label="Transform Data", mappings=[...])
p.connect(src=snap_api, dst=snap_mapper)  # Direct document → document connection
```

**Common APISuiteHTTPClient Patterns:**

```python
# GET request with query parameters
snap_get = APISuiteHTTPClient(
    label="GET Request",
    method="GET",
    url=Expr("'https://api.example.com/users/' + $user_id"),
    query_parameters=[
        APISuiteHTTPClient.QueryParametersItem(
            param_name="page",
            param_value=Expr("$page_num")
        )
    ]
)

# POST request with JSON body
snap_post = APISuiteHTTPClient(
    label="POST Request",
    method="POST",
    url="https://api.example.com/users",
    headers=[
        APISuiteHTTPClient.HeadersItem(
            header_name="Content-Type",
            header_value="application/json"
        )
    ],
    request_body=Expr("JSON.stringify($user_data)")
)

# Request with authentication
snap_auth = APISuiteHTTPClient(
    label="Authenticated Request",
    method="GET",
    url="https://api.example.com/protected",
    auth_type="Bearer",
    auth_token=Expr("_api_token")
)
```

**API Response Array Splitting:**

`APISuiteHTTPClient` returns a single document with the structure `{statusLine, headers, entity: [...]}`. When the `entity` field is an array, you need to split it into individual documents for downstream processing:

**Pattern A: JSON Splitter (default/recommended)**
```python
snap_api = APISuiteHTTPClient(
    label="Fetch Data",
    http_method='GET',
    uri='https://api.example.com/items',
    client_properties=APISuiteHTTPClient.ClientProperties(
        output_props=APISuiteHTTPClient.ClientProperties.OutputProps(
            response_type='JSON'
        )
    )
)

snap_splitter = TransformJSONSplitter(
    label="Split Entity Array",
    path='$.entity',
    null_safe_access=True
)
p.connect(src=snap_api, dst=snap_splitter, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
```

**Pattern B: Entity Extraction (more concise)**
```python
snap_api = APISuiteHTTPClient(
    label="Fetch Data",
    http_method='GET',
    uri='https://api.example.com/items',
    client_properties=APISuiteHTTPClient.ClientProperties(
        output_props=APISuiteHTTPClient.ClientProperties.OutputProps(
            extract_entity=True,
            extract_entity_path=Expr("$.entity"),
            response_type='JSON'
        )
    )
)
# No splitter needed — snap_api outputs one document per array element
```

> **Critical — quoting rule for `extract_entity_path`:**
> The path must be a **bare document field reference**, not a string literal:
> ```python
> # CORRECT — $.entity is a document field reference
> extract_entity_path=Expr("$.entity")
>
> # WRONG — inner quotes make this a string literal, not a path expression
> extract_entity_path=Expr("'$.entity'")
> ```

**APISuiteHTTPClient View Constraints:**

| View Type | Min | Max | Notes |
|-----------|-----|-----|-------|
| Input | 0 | 1 | Request data from upstream |
| Output | 0 | **1** | Response data (**document** by default) - only ONE output view supported |
| Error | - | - | Configured via "When errors occur" setting |

**Important:** The HTTP Client snap does NOT support multiple output views.

**Authentication Patterns:**

```python
# OAuth 2.0
snap_0 = APISuiteHTTPClient(
    label='OAuth API Call', method='GET',
    url='https://api.example.com/v1/data',
    auth_type='OAuth2',
    oauth_account='$_oauthAccount'
)

# API Key
snap_0 = APISuiteHTTPClient(
    label='API Key Authentication', method='GET',
    url='https://api.example.com/v1/data',
    headers=[
        APISuiteHTTPClient.HeadersItem(header_name='X-API-Key', header_value='$_apiKey'),
        APISuiteHTTPClient.HeadersItem(header_name='Content-Type', header_value='application/json')
    ]
)

# Bearer Token
snap_0 = APISuiteHTTPClient(
    label='Bearer Token Authentication', method='POST',
    url='https://api.example.com/v1/orders',
    headers=[
        APISuiteHTTPClient.HeadersItem(header_name='Authorization', header_value=Expr('"Bearer " + $_accessToken')),
        APISuiteHTTPClient.HeadersItem(header_name='Content-Type', header_value='application/json')
    ]
)
```

### Rule 4: Script Snap Usage (LAST RESORT ONLY)

**Script Snap should be the LAST RESORT** after verifying that native snaps cannot achieve the requirement. See §7 Snap Reference for comprehensive Script Snap documentation.

**Script Snap Limitations:**
- **Python 2.7.2 only** (Jython) - No Python 3.x features
- **Performance impact** - 10-50x slower than native snaps
- **Maintenance complexity** - Custom code harder to debug and maintain
- **Cannot spawn processes** on Cloudplex (cloud environment)
- **Limited libraries** - Only standard library and select third-party packages

**Before using Script Snap, verify you CANNOT use:**
1. **TransformMapper** - For data transformations, field mapping, calculations
2. **Expression Libraries (.expr)** - For complex reusable logic with expressions
3. **Native Snaps** - Database operations, API calls, file operations
4. **APISuiteHTTPClient** - For REST API integration
5. **Flow Snaps** - Router, Filter, Copy, Gate for control flow

**ONLY justified when:**
- Requires specific Java library with no REST API alternative
- Custom algorithm that cannot be expressed in SnapLogic expressions
- Legacy system integration with proprietary protocol
- Python 2.7.2 limitations are acceptable for the use case

### Rule 5: Child Pipeline References (FlowPipelineExecute)

When using FlowPipelineExecute to call child pipelines, the `pipeline` parameter MUST use literal names (not expressions) to enable slpy-inliner detection for automatic inlining.

**Pipeline name convention:** `pipeline=` must match the child pipeline's label (`Pipeline(label=...)`). Do NOT include `.py` extension — the platform resolves by pipeline name, not filename. In `slpy exec`, PCC resolves the name to a `.py` file in the parent's directory by convention (e.g., `pipeline="my_child"` finds `my_child.py`).

```python
# CORRECT - Literal Pipeline Name
snap_2 = FlowPipelineExecute(
    label="Execute Child Pipeline",
    pipeline="ST001_INSPECTIONS",  # Literal name - slpy-inliner can detect
    params=[
        FlowPipelineExecute.ParamsItem(
            param_name="FileName",
            param_value=Expr("_DeltaFileName")  # Expr OK for param VALUES
        )
    ]
)

# WRONG - Expression for Pipeline Name
snap_2 = FlowPipelineExecute(
    label="Execute Child Pipeline",
    pipeline=Expr("_pipeline_path"),  # ERROR: slpy-inliner cannot detect
)
```

**IMPORTANT DISTINCTION:**
- `pipeline=` parameter → MUST be literal string
- `params=` list → CAN contain Expr() wrappers for parameter values being passed

**Why this matters:**
- slpy-inliner tool scans SLPy files for literal pipeline names
- Enables automatic pipeline inlining for optimization
- Improves dependency detection and validation

**For 99% of cases (especially orchestrators), use literal names.**

### Rule 6: Reader Snap Connections

Reader Snaps (File Reader, S3 Reader, Database Read, API calls) typically DO NOT require input connections unless specific conditions apply.

```python
# CORRECT - Reader without Input
snap_0 = BinaryFileReader(label="Read CSV File", file_path="/data/input.csv")
snap_1 = TransformCSVParser(...)
p.connect(src=snap_0, dst=snap_1)

# WRONG - Unnecessary Input Connection
snap_0 = BinaryFileReader(...)
p.connect(src=OPEN_VIEW.INPUT, dst=snap_0, src_view_id="INPUT", dst_view_id="input0")  # ERROR: Unnecessary
```

**When Reader Snaps DO need input connections:**
1. **Dynamic File Paths** - Path comes from upstream document
2. **Parent-Child Pipeline Configuration** - Configuration passed from parent
3. **Conditional Triggering** - Reader only executes for certain records

**Best Practice:** Start pipelines with Reader snaps (no input) unless dynamic behavior requires upstream data.

### Rule 7: Expression Library Restrictions

Expression libraries (.expr files) contain reusable functions and constants referenced in pipelines via the `lib` global. They have STRICT syntax restrictions — see §9 for the complete canonical list and validation checklist.

**CRITICAL:** Expression libraries are NOT full JavaScript/Python - they are LIMITED to single-expression arrow functions.

**ALLOWED in .expr files:**
- Object literals with key-value pairs
- Single-expression arrow functions: `param => expression`
- Ternary operators: `condition ? value1 : value2`
- Method chaining: `.map().filter().reduce()`
- Arithmetic and logical operators: `+, -, *, /, ==, !=, &&, ||`
- Built-in functions: `Math.*`, `Date.now()`, `Date.parse()`, etc.
- String coercion via concatenation: `'' + expr`

**ABSOLUTELY FORBIDDEN in .expr files:**
- Multi-line function blocks with braces `{ }`
- `return` statements
- Variable declarations: `var`, `let`, `const`
- `if/else` statements (use ternary `? :`)
- Loops: `for`, `while`, `do/while` (use `.map()`, `.filter()`)
- Strict equality: `===`, `!==` (use `==`, `!=`)
- Increment/decrement: `++`, `--` (use `+= 1`)
- Assignment operators: `+=`, `-=`, `*=`, `/=`
- `this.otherFunction()` cross-references — silently returns null in `slpy exec`
- Comments: `/* */` and `//` — the parser tokenizes them as expressions
- `String()`, `Number()`, `Boolean()` constructors — return null. Use `'' + expr`, `parseFloat(x)`, `x == 'true'` instead
- IIFE `(function() { ... })()` — parse error. Inline the logic as a single arrow expression
- Object literal `{...}` as root of `Expr()` — returns null in TransformMapper

**Conversion Examples (Wrong → Correct):**

```javascript
// BEFORE (Multi-line with if/else) - WRONG
calculate_shipping: (weight, zone) => {
    if (zone == 'domestic') {
        if (weight < 5) return 10;
        else return 15;
    } else {
        if (weight < 5) return 25;
        else return 40;
    }
}

// AFTER (Nested ternary) - CORRECT
calculate_shipping: (weight, zone) =>
    zone == 'domestic' ?
        (weight < 5 ? 10 : 15) :
        (weight < 5 ? 25 : 40)

// BEFORE (Variable declaration) - WRONG
get_full_address: (street, city, state, zip) => {
    const line1 = street;
    const line2 = city + ', ' + state + ' ' + zip;
    return line1 + '\n' + line2;
}

// AFTER (Direct chaining) - CORRECT
get_full_address: (street, city, state, zip) =>
    street + '\n' + city + ', ' + state + ' ' + zip

// BEFORE (For loop) - WRONG
filter_active: (users) => {
    const active = [];
    for (let i = 0; i < users.length; i++) {
        if (users[i].status == 'active') {
            active.push(users[i]);
        }
    }
    return active;
}

// AFTER (Filter method) - CORRECT
filter_active: (users) => users.filter(u => u.status == 'active')
```

### Rule 8: TransformGroupByFields Output Structure

The SnapLogic platform's `TransformGroupByFields` snap wraps group-by field values under a **`groupBy`** key in the output document. This is hardcoded behavior — NOT configurable.

**Platform output structure:**
```json
{
  "groupBy": { "continent": "Africa", "region": "East" },
  "<target_field>": [ ... grouped records ... ]
}
```

- The `target_field` parameter controls where the **grouped records list** goes (default: `"group"`)
- The group-by field values **always** appear under `$groupBy`, never at the document root
- Downstream snaps must use `$groupBy.<field>` to access group-by key values

**`slpy exec` parity:** The local executor matches the platform — `slpy exec` wraps group-by field values under `$groupBy` identically.

**Sorting requirement:** `TransformGroupByFields` requires input sorted by the group-by fields for correct global grouping. Always place a `TransformSort` immediately before `TransformGroupByFields`.

```python
# CORRECT — Full pattern with downstream $groupBy references
snap_sort = TransformSort(label="Sort by Continent", sort_order=[("continent", "asc")])

snap_group = TransformGroupByFields(
    label="Group by Continent",
    fields=[TransformGroupByFields.FieldsItem(field="continent")],
    target_field="countries"
)

snap_map = TransformMapper(
    label="Format Grouped Output",
    mapping={
        "continent": Expr("$groupBy.continent"),  # Group key under $groupBy
        "country_count": Expr("$countries.length"),
        "countries": Expr("$countries")
    }
)

snap_sort > snap_group > snap_map
```

### Rule 9: BinaryFileReader vs BinaryFileWriter Parameter Names (COMMON CONFUSION)

BinaryFileReader and BinaryFileWriter use DIFFERENT parameter names for the file path. This is a platform inconsistency that frequently causes errors.

| Snap | Parameter | Example |
|------|-----------|---------|
| BinaryFileReader | `file_path` | `file_path='input.csv'` |
| BinaryFileWriter | `filename` | `filename='output.json'` |

```python
# CORRECT
BinaryFileReader(file_path='data.csv')
BinaryFileWriter(filename='output.json', file_action='OVERWRITE')

# WRONG
BinaryFileReader(filename='data.csv')       # ERROR: no 'filename' parameter
BinaryFileWriter(file_path='output.json')   # ERROR: no 'file_path' parameter
```

### Rule 10: Account References (pm_account)

Snaps bind to platform connection accounts via `pm_account`. There are two valid forms:

```python
# Static binding — references one specific account asset
snap_0 = APISuiteHTTPClient(
    label='Call API', http_method='POST', uri='https://example.com',
    pm_account=Account(
        ref_class_id='com-snaplogic-snaps-apisuite-accounts-headerauthaccount',
        label='my-account',
        ref_id='...'
    )
)

# Expression binding — resolved at runtime, typically from an expression library,
# so the same pipeline works across Dev/Test/Prod environments
snap_0 = APISuiteHTTPClient(
    label='Call API', http_method='POST', uri='https://example.com',
    pm_account=Expr('lib.env.httpClientAccount')
)
```

**Preservation rules when editing an existing pipeline:**
- **NEVER remove, rewrite, or "simplify" a `pm_account=Expr('lib.env.*')` binding** unless the user explicitly asks to change the account. It is a deliberate environment-independence mechanism, not a label — replacing it with a static account (or dropping it) breaks the pipeline in every other environment.
- Leave `pm_account` exactly as found on snaps whose accounts you weren't asked to touch.
- **NEVER pass a bare string** (`pm_account="lib.env.acct"`) — the parser silently produces an empty account binding. Use `Expr(...)` for expression refs or `Account(...)` for static refs.
- SnapCode cannot create account assets; a static `Account(...)` must reference one that already exists on the platform (see deploy-skill limitations).

### Never Guess — Consult Tools

Always call `pygen_validate_snap_names(do_get_parameters=True)` for exact parameter names, types, and Expr()-eligibility. Call `pygen_get_snap_io_info` for connection types. Call `pygen_get_snap_documentation` for behavior you're unsure about. There are 900+ snaps — tools are the source of truth.

## 6. SLPy Format Reference

### 6.1 SLPy Language Constraints

**CRITICAL**: SLPy (SnapLogic Python format) is a **limited subset of Python** used solely for declaring pipeline structure. It is **NOT executable Python code** and must be converted to SLP JSON format for import and execution in the SnapLogic platform.

#### What SLPy IS:
- A **declarative format** for defining SnapLogic pipeline structure
- A **limited subset** of Python syntax
- A **non-executable** representation that requires conversion to SLP JSON

#### Allowed Python Constructs in SLPy:
1. **Import statements** (only from slpy.modules):
   ```python
   from slpy.modules.Pipeline import Pipeline
   from slpy.modules.Pipeline.utils.open_view import OPEN_VIEW
   from slpy.modules.Snap.{SnapName} import {SnapName}
   ```

2. **Pipeline instantiation**:
   ```python
   p = Pipeline()
   # or with label
   p = Pipeline(label='Pipeline Name')
   ```

3. **Snap instantiation** with configuration:
   ```python
   snap_0 = TransformMapper(pass_through=False,
                           transformations=TransformMapper.Transformations(...))
   ```

4. **Connection definitions**:
   ```python
   p.connect(src=snap_0, dst=snap_1, src_view_id="output0", dst_view_id="input0",
             src_output_type="document", dst_input_type="document")
   ```

5. **Python docstrings** for documentation

#### NOT Allowed in SLPy:
- Functions (def)
- Classes (class)
- Loops (for, while)
- Conditionals (if, else)
- Variables (except pipeline and snap instances)
- Any executable Python code
- Python expressions or operations
- External library imports

**If you find yourself wanting to use any of the above forbidden constructs, you are generating INVALID code. Stop and rewrite using only allowed patterns.**

### 6.2 Pipeline Architecture

#### Pipeline Structure
Every SLPy pipeline follows this structure:

```python
"""
Pipeline Name: Descriptive Pipeline Name

Pipeline Summary: Brief description of what the pipeline does.

(#snap_0) SnapName: Description of what this snap does
(#snap_1) SnapName: Description of what this snap does
"""

# Import statements
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.utils.open_view import OPEN_VIEW
from slpy.modules.Snap.SnapName1 import SnapName1
from slpy.modules.Snap.SnapName2 import SnapName2

# Optional imports for pipeline configuration
from slpy.modules.Pipeline.param_table.ParamTable import ParamTable
from slpy.modules.Pipeline.error_pipeline.ErrorPipeline import ErrorPipeline
from slpy.modules.Pipeline.error_param_table.ErrorParamTable import ErrorParamTable
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries
from slpy.modules.Pipeline.utils import Expr

p = Pipeline(label='Pipeline Name')

# Optional: Define pipeline parameters
p.param_table = ParamTable(param=[
    ParamTable.ParamItem(
        capture=True,
        key='parameterName',
        value='defaultValue',
        data_type='string'
    )
])

# Optional: Reference error handling pipeline
p.error_pipeline = ErrorPipeline(value='path/to/error/pipeline')

# Optional: Pass parameters to error pipeline
p.error_param_table = ErrorParamTable(error_param=[
    ErrorParamTable.ErrorParamItem(
        value=Expr('pipe.ruuid'),
        key='pipe_ruuid'
    )
])

# Optional: Import expression libraries
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/helpers.expr',
        as_='helpers'
    )
])

# Snap instantiation
snap_0 = SnapName1(configuration_parameters)
snap_1 = SnapName2(configuration_parameters)

# Connections
p.connect(src=snap_0, dst=snap_1, ...)
```

#### Data Types
1. **Document**: JSON documents (primary data type)
2. **Binary**: Raw binary data (files, streams)

#### View Types
- **Input views**: Where Snaps receive data
- **Output views**: Where Snaps send data
- **OPEN_VIEW.INPUT**: Pipeline's external input
- **OPEN_VIEW.OUTPUT**: Pipeline's external output

### 6.3 Pipeline Parameters

Pipeline parameters enable dynamic configuration and are essential for parent-child pipeline communication.

#### Parameter Definition and Access
- Parameters are prefixed with underscore: `_parameterName`
- Can be used in expressions and Snap configurations
- Passed between pipelines via FlowPipelineExecute

#### Defining Pipeline Parameters

Pipeline parameters must be defined in the pipeline's `param_table` property before use:

```python
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.param_table.ParamTable import ParamTable

p = Pipeline(label='My Pipeline')

p.param_table = ParamTable(param=[
    ParamTable.ParamItem(
        capture=True,           # Required: enables parameter capture
        key='api_key',          # Required: parameter name (no underscore prefix here)
        value='default_value',  # Required: default value
        data_type='string'      # Optional: data type (default: 'string')
    ),
    ParamTable.ParamItem(
        capture=True,
        key='batch_size',
        value='100',            # All parameter values are strings
        data_type='string'
    ),
    ParamTable.ParamItem(
        capture=True,
        key='enable_debug',
        value='false',          # Boolean as string
        data_type='string'
    )
])
```

**Key Points:**
- All parameters must have `capture=True` to enable parameter capture
- The `key` field is the parameter name WITHOUT underscore prefix
- The `value` field is ALWAYS a string (even for numbers and booleans)
- Access in expressions using `_parameterName` (WITH underscore prefix)

#### Built-in Pipeline Properties

SnapLogic provides built-in pipeline properties accessible via `pipe.*` prefix:

```python
pipe.ruuid          # Pipeline runtime UUID
pipe.label          # Pipeline label/name
pipe.user           # User who triggered the pipeline
pipe.projectPath    # Project path where pipeline resides
```

**Example usage in TransformMapper**:
```python
snap_0 = TransformMapper(
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("pipe.ruuid"),
                target_path="$.pipeline_run_id"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("pipe.user + '@' + pipe.label"),
                target_path="$.execution_context"
            )
        ]
    )
)
```

#### Type Conversion for Parameters

Since all pipeline parameters are strings, convert them when needed:

```python
# Numeric operations
expression=Expr("parseInt(_batch_size) * 2")

# Float operations
expression=Expr("parseFloat(_threshold) * 1.1")

# Boolean conversion
expression=Expr("_enable_debug == 'true'")
```

#### Parameter Usage in FlowPipelineExecute
```python
snap_0 = FlowPipelineExecute(
    pipeline='child_pipeline',  # Pipeline label — no path prefix, no .py extension
    params=[
        FlowPipelineExecute.ParamsItem(param_name='inputFile', param_value='data.csv'),
        FlowPipelineExecute.ParamsItem(param_name='batchSize', param_value='1000'),
        FlowPipelineExecute.ParamsItem(param_name='environment', param_value='production')
    ],
    batch_size=10,
    pool_size=5,
    retry_limit=3,
    retry_interval=5
)
```

#### Accessing Parameters in Expressions
```python
# In TransformMapper expressions
expression=Expr('_environment + "_" + $.tableName')

# In file paths
file_path=Expr('"data/" + _inputFile')

# In conditional logic
expression=Expr('_batchSize > 100 ? "large" : "small"')
```

#### Parameter Naming Conventions
- Use camelCase: `_inputFile`, `_batchSize`
- Be descriptive: `_sourceDatabase`, not `_db`
- Indicate type when helpful: `_maxRetryCount`, `_enableDebugFlag`

### 6.4 Error Pipeline Configuration

Error pipelines handle errors globally for a pipeline. Unlike error views (which route errors within a pipeline), error pipelines are separate pipelines invoked when unhandled errors occur.

#### Defining Error Pipeline

```python
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.error_pipeline.ErrorPipeline import ErrorPipeline
from slpy.modules.Pipeline.error_param_table.ErrorParamTable import ErrorParamTable
from slpy.modules.Pipeline.utils import Expr

p = Pipeline(label='Main Pipeline')

# Reference the error handling pipeline
p.error_pipeline = ErrorPipeline(
    value='shared/Error_Handler'  # Path to error pipeline
)

# Pass parameters to error pipeline
p.error_param_table = ErrorParamTable(error_param=[
    ErrorParamTable.ErrorParamItem(
        value=Expr('pipe.ruuid'),      # Pipeline runtime ID
        key='pipe_ruuid'
    ),
    ErrorParamTable.ErrorParamItem(
        value=Expr('pipe.label'),      # Pipeline name
        key='pipe_label'
    ),
    ErrorParamTable.ErrorParamItem(
        value=Expr('pipe.user'),       # User who triggered pipeline
        key='pipe_user'
    ),
    ErrorParamTable.ErrorParamItem(
        value=Expr('_tableName'),      # Custom parameter from parent
        key='tableName'
    ),
    ErrorParamTable.ErrorParamItem(
        value='CRITICAL',              # Static value (no Expr needed)
        key='severity'
    )
])
```

**Key Points:**
- `error_pipeline` references the path to error handling pipeline
- `error_param_table` passes parameters to the error pipeline
- Use `Expr()` for dynamic values (pipeline properties, parameters)
- Static values don't need `Expr()` wrapper
- Error parameters can access pipeline properties via `pipe.*`

#### Error Pipeline vs Error Views

| Feature | Error Pipeline | Error Views |
|---------|----------------|-------------|
| **Scope** | Global (entire pipeline) | Local (specific Snap) |
| **Invocation** | Unhandled errors only | Controlled by Snap's `error_policy` |
| **Definition** | Separate pipeline | Connections within same pipeline |
| **Use case** | Centralized error logging/alerting | Snap-specific error handling |

**Best Practice**: Use error views for expected errors (parsing, validation), error pipelines for unexpected failures.

### 6.5 Connection Syntax & Patterns

#### Connection Syntax
```python
p.connect(
    src=source_snap,           # Source snap or OPEN_VIEW.INPUT
    dst=destination_snap,      # Destination snap or OPEN_VIEW.OUTPUT
    src_view_id="output0",     # Source view ID
    dst_view_id="input0",      # Destination view ID
    src_output_type="document", # Source data type
    dst_input_type="document"   # Destination data type
)
```

#### View ID Conventions

**Source Views** (output from Snap):
- Standard: `"output0"`, `"output1"`, `"output2"`, ...
- Error: `"error0"`, `"error1"`, ...
- Special: `"OPEN_VIEW.INPUT"` (pipeline input)

**Destination Views** (input to Snap):
- Standard: `"input0"`, `"input1"`, `"input2"`, ...
- Extended (for Union): `"input101"`, `"input102"`, `"input103"`, ...
- Special: `"OPENVIEW.OUTPUT"` (pipeline output)

**Common Patterns**:
```python
# Multiple outputs (Router, Copy)
p.connect(src=snap_router, dst=snap_high, src_view_id="output0", ...)
p.connect(src=snap_router, dst=snap_low, src_view_id="output1", ...)

# Multiple inputs (Union)
p.connect(src=snap_0, dst=snap_union, dst_view_id="input0", ...)
p.connect(src=snap_1, dst=snap_union, dst_view_id="input1", ...)
p.connect(src=snap_2, dst=snap_union, dst_view_id="input101", ...)  # Extended input

# Error routing
p.connect(src=snap_parser, dst=snap_error_logger, src_view_id="error0", dst_view_id="input0", ...)
```

#### Type Compatibility Matrix

See **Rule 2** in §5 for the full type compatibility table and fixing patterns. Key rule: document→binary needs a **formatter** (TransformJSONFormatter, etc.), binary→document needs a **parser** (TransformJSONParser, etc.).
```

**WRONG - Type mismatch**:
```python
snap_0 = BinaryFileReader(...)    # Output: binary
snap_1 = TransformMapper(...)     # Input: document
p.connect(src=snap_0, dst=snap_1, ...)  # ERROR: binary -> document
```

**CORRECT - Add parser**:
```python
snap_0 = BinaryFileReader(...)         # Output: binary
snap_parser = TransformJSONParser()    # Input: binary, Output: document
snap_1 = TransformMapper(...)          # Input: document

p.connect(src=snap_0, dst=snap_parser, src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_parser, dst=snap_1, src_output_type="document", dst_input_type="document")
```

#### Common Connection Patterns

**Linear Pipeline**:
```python
p.connect(src=OPEN_VIEW.INPUT, dst=snap_0, src_view_id="OPEN_VIEW.INPUT", dst_view_id="input0", src_output_type="document", dst_input_type="document")
p.connect(src=snap_0, dst=snap_1, src_view_id="output0", dst_view_id="input0", src_output_type="document", dst_input_type="document")
p.connect(src=snap_1, dst=OPEN_VIEW.OUTPUT, src_view_id="output0", dst_view_id="OPENVIEW.OUTPUT", src_output_type="document", dst_input_type="document")
```

**Branching with Router**:
```python
# Router with multiple outputs
p.connect(src=snap_router, dst=snap_high, src_view_id="output0", dst_view_id="input0", ...)
p.connect(src=snap_router, dst=snap_low, src_view_id="output1", dst_view_id="input0", ...)
```

**Merging with Union**:
```python
# Multiple inputs to union
p.connect(src=snap_0, dst=snap_union, src_view_id="output0", dst_view_id="input0", ...)
p.connect(src=snap_1, dst=snap_union, src_view_id="output0", dst_view_id="input1", ...)
p.connect(src=snap_2, dst=snap_union, src_view_id="output0", dst_view_id="input101", ...)
```

**Process + Archive (Binary Fork)**:
```python
# Fork binary stream: one copy for processing, one for archive
snap_copy = FlowBinaryCopy(label='Fork Binary Stream')
p.connect(src=snap_reader, dst=snap_copy, src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_copy, dst=snap_processing, src_view_id="output0", dst_input_type="binary", ...)  # processing path
p.connect(src=snap_copy, dst=snap_archive_writer, src_view_id="output1", dst_input_type="binary", ...)  # archive path
```

### 6.6 SLPy Generation Rules

<Rules>
1. You must generate the Snap by Snap summary in the docstring before the pipeline code
2. The output must be valid Python code following SLPy constraints
3. Use only the Snap classes as they are defined - do not modify their structure
4. Respect minimum and maximum input/output views for each Snap
5. Ensure output types match input types when connecting Snaps
6. Binary outputs can only connect to binary or document+binary inputs
7. Document outputs can only connect to document or document+binary inputs
8. Each connection must have unique src/dst view combinations
9. Include all required configuration parameters for each Snap
10. Use proper Python syntax for nested configuration objects
</Rules>

---

## Reference Documentation (On-Demand)

The following reference files are available in the `references/` directory. **Read these files on-demand** using the Read tool when you need detailed information for the current pipeline.

| File | Contents | When to Read |
|------|----------|--------------|
| `references/programming_model.md` | Foundational SnapLogic primer: snaps, pipelines, data types, connection semantics | When unfamiliar with SnapLogic concepts or onboarding |
| `references/cdc_patterns.md` | Change Data Capture implementation patterns for SLPy pipelines (hash-based CDC) | When building CDC or delta-detection pipelines |

## 7. Snap Reference

### 7.1 Snap Categories by Pipeline Phase

SnapLogic pipelines typically follow a pattern: **READ -> PARSE -> TRANSFORM -> FORMAT -> WRITE**

#### 1. READ Phase (Data Ingestion)

Extract data from various sources:

**File Operations**:
- `BinaryFileReader`: Read files from filesystem, SFTP, S3, etc.
- `BinaryDirectoryBrowser`: List files in a directory
- `BinaryFilePoller`: Poll for new files matching pattern

**Database Operations** (Read snaps):
- `SnowflakeExecute`: Execute Snowflake queries
- `MySQLExecute`, `OracleSelect`, `PostgreSQLSelect`: Database-specific readers
- `RedshiftSelect`: Amazon Redshift queries

**Cloud Services**:
- `BinaryS3FileReader`: Read from AWS S3
- Azure Blob/File Storage: use `BinaryFileReader` with SAS URI, or `APISuiteHTTPClient` with Azure REST API
- GCP Storage: use `APISuiteHTTPClient` with GCS JSON API + service account token

**API/HTTP**:
- `APISuiteHTTPClient`: HTTP REST API calls (GET, POST, etc.) -- outputs **document** data by default, so the PARSE phase can be skipped for API calls
- **DO NOT USE**: `RestGet`, `RestPost`, `RestPut`, `RestDelete` (deprecated)

**Application-Specific**:
- `SalesforceRead`, `ServiceNowQuery`, `WorkdayRead`, etc.

**Data Generation**:
- `TransformJSONGenerator`: Generate documents from inline JSON — `editable_content=json.dumps(data)` (must be a JSON **string**, not a Python object), `array_elements_as_documents=True` to emit each array element as a separate document

---

#### 2. PARSE Phase (Structuring Data)

Convert unstructured/semi-structured data to JSON documents:

- `TransformCSVParser`: Parse CSV/TSV files -> JSON documents
- `TransformJSONParser`: Parse JSON strings -> JSON documents
- `TransformXMLParser`: Parse XML -> JSON documents
- `TransformExcelParser`: Parse Excel (.xlsx, .xls) -> JSON documents
- `TransformAvroParser`: Parse Avro -> JSON documents
- `TransformParquetParser`: Parse Parquet -> JSON documents

**Note**: Parsers typically accept **binary input** and produce **document output**. Parsers are needed after binary sources like file readers -- they are **NOT** needed after `APISuiteHTTPClient` when using document output (the default), since the HTTP Client already outputs structured documents.

---

#### 3. TRANSFORM Phase (Data Manipulation)

Modify, filter, aggregate, and route data:

**Field Mapping & Transformation**:
- `TransformMapper`: **Most common** - map/transform fields using expressions

**Filtering & Routing**:
- `FlowFilter`: Filter documents by condition (keeps matching documents)
- `FlowRouter`: Route to multiple outputs based on conditions (document type)
- `FlowBinaryRouter`: Route binary data based on conditions

**Aggregation & Grouping**:
- `TransformAggregate`: Aggregate data (sum, count, avg, etc.)
- `TransformGroupByFields`: Group documents by field values
  - **Params:** `fields=[TransformGroupByFields.FieldsItem(field="fieldName")]`, `target_field="groupedDocs"` — NOT `group_by=` (that param does not exist)
  - **Output structure:** Platform wraps group-by field values under a `groupBy` key -- downstream snaps must use `$groupBy.<field>` (not `$<field>`) to access group keys
  - **Sort required:** Input MUST be sorted by group-by fields first (`TransformSort` -> `TransformGroupByFields`) for correct global grouping
  - **`slpy exec` parity:** Local executor matches the platform -- both put group-by fields under `$groupBy`
- `TransformGroupByN`: Group every N documents into a single array document
  - **Params:** `group_size=10` (required, int), `target_field="batch"` — NOT `group_field=` (that param does not exist)

**Sorting**:
- `TransformSort`: Sort documents by field values

**Combining Data**:
- `FlowUnion`: Merge multiple streams (no key matching)
- `TransformJoin`: Join streams by key (LEFT, RIGHT, INNER, OUTER)

**Splitting**:
- `FlowCopy`: Duplicate stream to multiple outputs (document type)
  - **No parameters** — output view count is determined by `pipeline.connect()` calls, not by a config property. Do NOT pass `copy_count=` or similar.
- `FlowBinaryCopy`: Duplicate binary stream
- `TransformJSONSplitter`: Split JSON arrays into individual documents

**Control Flow**:
- `FlowExit`: Conditionally stop pipeline execution
- `FlowPipelineExecute`: Execute child pipelines

---

#### 4. FORMAT Phase (Prepare for Output)

Convert JSON documents to output format:

- `TransformJSONFormatter`: JSON documents -> JSON binary
- `TransformCSVFormatter`: JSON documents -> CSV binary
- `TransformXMLFormatter`: JSON documents -> XML binary
- `TransformExcelFormatter`: JSON documents -> Excel binary
- `TransformAvroFormatter`: JSON documents -> Avro binary
- `TransformParquetFormatter`: JSON documents -> Parquet binary

**IMPORTANT**: Formatters **always output binary** data. If used before another Snap, ensure downstream Snap accepts binary input or add a parser.

---

#### 5. WRITE Phase (Data Loading)

Load data into target systems:

**File Operations**:
- `BinaryFileWriter`: Write files to filesystem, SFTP, S3, etc.
- `BinaryFileDelete`: Delete files

**Database Operations** (Insert/Update/Upsert):
- `SnowflakeBulkLoad`, `SnowflakeInsert`, `SnowflakeUpdate`, `SnowflakeBulkUpsert`
- `MySQLInsert`, `OracleInsert`, `PostgreSQLInsert`: Database-specific writers
- `RedshiftBulkLoad`: Amazon Redshift bulk loading

**Cloud Services**:
- `BinaryS3FileWriter`: Write to AWS S3
- Azure Blob/File Storage: use `BinaryFileWriter` with SAS URI, or `APISuiteHTTPClient` with Azure REST API
- GCP Storage: use `APISuiteHTTPClient` with GCS JSON API + service account token

**API/HTTP**:
- `APISuiteHTTPClient`: HTTP REST API calls (POST, PUT, PATCH, DELETE)

**Application-Specific**:
- `SalesforceCreate`, `SalesforceUpdate`, `SalesforceUpsert`
- `ServiceNowInsert`, `WorkdayWrite`, etc.

---

#### Special Purpose Snaps

**ELT Snap Pack** (Database-Pushdown Operations):
- `ELTTransform`, `ELTJoin`, `ELTRouter`, `ELTPivot`, `ELTSort`, `ELTSelect`, `ELTLoad`
- **CRITICAL**: Do NOT mix ELT Snaps with non-ELT Snaps in same pipeline segment

### 7.2 Common Snap Configuration Patterns

#### TransformMapper
```python
TransformMapper(
    pass_through=True,      # Keep unmapped fields
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('$firstName + " " + $lastName'),
                target_path='$fullName'
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('$.price * 1.1'),
                target_path='$.priceWithTax'
            )
        ],
        mapping_root='$'
    )
)
```

#### FlowRouter
```python
FlowRouter(
    routes=[
        FlowRouter.RoutesItem(
            expression=Expr('$amount > 1000'),
            output_view_name='high_value'
        ),
        FlowRouter.RoutesItem(
            expression=Expr('$amount <= 1000'),
            output_view_name='low_value'
        )
    ],
    first_match=True  # Stop after first match
)
```

**FlowRouter connections:** `output0` = first `RoutesItem`, `output1` = second, etc. — order must match route definition order. For readability, you can also use the route's `output_view_name` as `src_view_id` (e.g., `src_view_id='high_value'`) — slpy remaps it to the correct positional ID at translate time.

#### Data Transformation Pattern
```python
# Read CSV -> Parse -> Transform -> Format -> Write
snap_0 = BinaryFileReader(file_path='data.csv')
snap_1 = TransformCSVParser(delimiter=',', contains_header=True)
snap_2 = TransformMapper(
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('upper($name)'),
                target_path='$name'
            )
        ]
    )
)
snap_3 = TransformJSONFormatter(pretty_print=True)
snap_4 = BinaryFileWriter(filename='output.json', file_action='OVERWRITE')
```

#### Parent-Child Pipeline Pattern
```python
# Parent pipeline
snap_execute = FlowPipelineExecute(
    pipeline='Child Pipeline',
    params=[
        FlowPipelineExecute.ParamsItem(param_name='batchId', param_value='12345')
    ],
    batch_size=100,
    pool_size=10
)

# Child pipeline accesses parameter
snap_mapper = TransformMapper(
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('_batchId'),
                target_path='$.processedBatchId'
            )
        ]
    )
)
```

#### Error Handling Pattern
```python
# Parse with error output
snap_parser = TransformCSVParser(
    error_policy='Both',  # Send errors to error view
    validate_headers=True
)

# Connect error view
p.connect(src=snap_parser, dst=snap_error_handler,
          src_view_id="error0", dst_view_id="input0", ...)
```

### 7.3 Binary vs Document Flow Control Pattern

When branching or copying data, choose between document and binary versions of Flow Snaps based on **downstream requirements** to minimize unnecessary formatters.

#### Problem: Multiple Formatters

**INEFFICIENT - Multiple formatters after copy**:
```python
snap_0 = TransformCSVParser()         # Output: document
snap_1 = FlowCopy()                   # Document copy, 2 outputs
snap_2 = TransformJSONFormatter()     # Formatter #1
snap_3 = TransformJSONFormatter()     # Formatter #2 (duplicate!)
snap_4 = BinaryFileWriter(...)
snap_5 = BinaryFileWriter(...)

p.connect(src=snap_0, dst=snap_1, src_output_type="document", dst_input_type="document")
p.connect(src=snap_1, dst=snap_2, src_view_id="output0", src_output_type="document", dst_input_type="document")
p.connect(src=snap_1, dst=snap_3, src_view_id="output1", src_output_type="document", dst_input_type="document")
p.connect(src=snap_2, dst=snap_4, src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_3, dst=snap_5, src_output_type="binary", dst_input_type="binary")
```

#### Solution: Format Before Binary Copy

**EFFICIENT - Single formatter before binary copy**:
```python
snap_0 = TransformCSVParser()         # Output: document
snap_1 = TransformJSONFormatter()     # Single formatter
snap_2 = FlowBinaryCopy()             # Binary copy, 2 outputs
snap_3 = BinaryFileWriter(...)
snap_4 = BinaryFileWriter(...)

p.connect(src=snap_0, dst=snap_1, src_output_type="document", dst_input_type="document")
p.connect(src=snap_1, dst=snap_2, src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_2, dst=snap_3, src_view_id="output0", src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_2, dst=snap_4, src_view_id="output1", src_output_type="binary", dst_input_type="binary")
```

**Result**: Eliminated duplicate formatter, reduced complexity.

#### Flow Snap Pairs

| Document Version | Binary Version | Use Case |
|-----------------|----------------|----------|
| `FlowCopy`      | `FlowBinaryCopy` | Duplicate data streams |
| `FlowRouter`    | `FlowBinaryRouter` | Conditional routing |

#### Decision Rule

**Before adding FlowCopy or FlowRouter:**
1. Check downstream Snap input types
2. If **all downstream Snaps require binary**: Format first, then use **Binary** version
3. If **all downstream Snaps require document**: Use **Document** version
4. If **mixed**: Use document version and format individual branches

**Example with Router**:

**INEFFICIENT**:
```
TransformMapper -> FlowRouter (document) -> TransformJSONFormatter -> BinaryFileWriter
                            -> TransformJSONFormatter -> BinaryFileWriter
```

**EFFICIENT**:
```
TransformMapper -> TransformJSONFormatter -> FlowBinaryRouter (binary) -> BinaryFileWriter
                                                                        -> BinaryFileWriter
```

### 7.4 ELT Snap Pack Isolation

**ELT Snaps** (ELTJoin, ELTRouter, ELTPivot, ELTSort, ELTSelect, ELTLoad, ELTTransform) perform transformations **within the database** for performance.

**CRITICAL**: Do NOT mix ELT Snaps with non-ELT Snaps in the same pipeline segment.

**WRONG - Mixed ELT and non-ELT**:
```python
snap_0 = SnowflakeExecute(...)       # Non-ELT
snap_1 = ELTTransform(...)        # ELT
snap_2 = TransformMapper(...)     # Non-ELT
snap_3 = ELTLoad(...)             # ELT
```

**CORRECT - All ELT**:
```python
snap_0 = SnowflakeExecute(...)       # Non-ELT (reads data)
snap_1 = ELTTransform(...)        # ELT
snap_2 = ELTFilter(...)           # ELT
snap_3 = ELTLoad(...)             # ELT
```

**CORRECT - All non-ELT**:
```python
snap_0 = SnowflakeExecute(...)       # Non-ELT
snap_1 = TransformMapper(...)     # Non-ELT
snap_2 = FlowFilter(...)          # Non-ELT
snap_3 = SnowflakeBulkLoad(...)   # Non-ELT
```

**Why?** ELT Snaps push operations to the database engine. Mixing with non-ELT forces data to move between SnapLogic and the database, negating performance benefits.

### 7.5 Script Snap

---
**IMPORTANT: SCRIPT SNAP SHOULD BE LAST RESORT ONLY**

**Before using Script Snap, verify you CANNOT use:**
- **TransformMapper** (for data transformation, calculations, field mapping)
- **TransformJSONParser/CSVParser** (for parsing and format conversion)
- **FlowFilter/FlowRouter** (for filtering and conditional routing)
- **APISuiteHTTPClient** (for HTTP/REST API calls -- outputs documents directly, no parser needed)
- **Expression Libraries** (for complex reusable logic)
- **UnixExecute** (for shell commands on Groundplex)
- **Database-specific Snaps** (for SQL operations)

**Why Strongly Avoid Script Snap?**
1. **Performance**: 10-50x slower than native Snaps for data processing
2. **Limitations**: Python 2.7.2 only (Jython), no Python 3.x support
3. **Maintenance**: Embedded code is harder to test, debug, and version control
4. **Security**: Cannot spawn external processes on Cloudplex
5. **Libraries**: Most Python libraries are incompatible with Jython
6. **Best Practice**: SnapLogic recommends using native Snaps for better performance and maintainability

**Script Snap is justified ONLY when:**
- Requires specific Java library access NOT available via REST API
- Logic absolutely CANNOT be expressed in SnapLogic expression language
- NO native Snap can achieve the requirement (verified through documentation)
- Performance impact is acceptable (not high-volume processing)

---

The **Script** Snap enables execution of custom JavaScript, Python, or Ruby scripts within SnapLogic pipelines using the JVM ScriptEngine mechanism. No account configuration is required.

**CRITICAL LIMITATION**: The Script Snap supports **Python 2.7.2 only** (via Jython 2.7.2). Python 3.x is NOT supported.

**Preferred language:** Always use `language='Python'` unless the use case specifically requires Java library access via JavaScript. Omit `language` only if JavaScript is intentionally needed (it's the default).

#### Overview

| Property | Details |
|----------|---------|
| Snap Type | Write-type Snap |
| Scripting Languages | JavaScript, Python (Jython 2.7.2), Ruby |
| Input Views | 0-1 document input views |
| Output Views | 0-1 document output views |
| Ultra Pipeline Support | Yes (with lineage requirements) |

#### Key Configuration Parameters

**Basic Configuration (inline script):**
```python
snap_0 = Script(
    label='Custom Script Logic',
    language='Python',  # Preferred: 'Python'. Also: 'Javascript' (default), 'Ruby'
    editable_content='''
from com.snaplogic.scripting.language import ScriptHook

class TransformScript(ScriptHook):
    def __init__(self, input, output, error, log):
        self.input = input
        self.output = output
        self.error = error
        self.log = log

    def execute(self):
        while self.input.hasNext():
            doc = self.input.next()
            wrapper = {"original": doc, "processed": True}
            self.output.write(doc, wrapper)

hook = TransformScript(input, output, error, log)
'''
)
```

**IMPORTANT:** Inline code uses `editable_content=` (not `script=`). The `script=` parameter is for file URI references only.

**Alternative - Using Script File:**
```python
snap_0 = Script(
    label='Custom Script Logic',
    language='Python',
    script='file:///transform.py'  # File URI from SLDB, supports pipeline parameters
)
```

#### ScriptHook Interface

The Script Snap provides access to input and output views through a standard interface:

**JavaScript:**
```javascript
// Check for input availability
this.input.hasNext()

// Read next document
var doc = this.input.next()

// Write to output (with lineage for Ultra pipelines)
this.output.write(inputDoc, outputDoc)
```

**Python (Jython 2.7.2):**
```python
# Check for input availability
self.input.hasNext()

# Read next document
doc = self.input.next()

# Write to output (with lineage for Ultra pipelines)
self.output.write(input_doc, output_doc)

# Write to error view (with lineage)
self.error.write(input_doc, error_doc)

# Logging
self.log.info("Processing document")
self.log.warn("Potential issue")
self.log.error("Failed to process")
```

**Complete pattern requirement:** Scripts must define a class extending `ScriptHook` with `__init__(self, input, output, error, log)` and `execute(self)` methods. The class must be instantiated at module level: `hook = ClassName(input, output, error, log)`. Bare `self.input.hasNext()` without the class pattern will not work on the platform. See the Basic Configuration example above.

#### Python 2.7.2 (Jython) Limitations and Breaking Changes

**CRITICAL**: The Script Snap uses Jython 2.7.2, which has significant limitations:

1. **Python 2.7 Only**: No Python 3.x syntax or features are supported
2. **BigInteger Handling**: Jython 2.7.2 automatically converts BigInteger to primitive long
   - **Problem**: Code like `sum = a.intValue() + b.intValue()` will fail
   - **Solution**: Use direct arithmetic: `sum = a + b`

3. **Dictionary Key Errors**: Missing keys now raise `KeyError` instead of returning `None`
   - **Problem**: `my_dict['missing_key']` raises `KeyError`
   - **Solution**: Use `.get()` method: `my_dict.get('missing_key')`

4. **String Encoding**: Some operations require explicit UTF-8 encoding
   - **Problem**: `zlib.compress(data)` may fail with unicode strings
   - **Solution**: `zlib.compress(data.encode("utf-8"))`

5. **Dictionary Methods**: Use direct subscript instead of `.toArray()`
   - **Problem**: `data.values().toArray()[0]` raises error
   - **Solution**: Use direct subscript: `data.values()[0]`

#### Ultra Pipeline Support Requirements

For Ultra pipelines, the `output.write()` method requires TWO arguments:

```python
# Ultra pipeline compatible
while self.input.hasNext():
    input_doc = self.input.next()
    output_doc = {"original": input_doc, "enriched_field": "value"}

    # First arg: input document (for lineage)
    # Second arg: output document (actual data)
    self.output.write(input_doc, output_doc)
```

This maintains request-response correlation in Ultra pipelines.

#### Security Restrictions

- **Cloudplex**: Cannot create external processes (e.g., `popen`)
- **Groundplex**: External process creation possible (can be disabled by support)

#### Example Configurations

**JavaScript - Data Transformation:**
```python
snap_0 = Script(
    label='Enrich Documents with JS',
    script='''
importClass(java.util.LinkedHashMap);

while (this.input.hasNext()) {
    var inDoc = this.input.next();
    var outDoc = new LinkedHashMap();
    outDoc.put("original", inDoc);
    outDoc.put("timestamp", Date.now());
    outDoc.put("processed", true);
    this.output.write(inDoc, outDoc);
}
'''
)
```

**Python - Simple Filtering:**
```python
snap_0 = Script(
    label='Filter High Value Records',
    language='Python',
    script='''
while self.input.hasNext():
    doc = self.input.next()
    # Python 2.7 syntax
    if doc.get('amount', 0) > 1000:
        output_doc = {
            "original": doc,
            "category": "high_value"
        }
        self.output.write(doc, output_doc)
'''
)
```

**Python with Pipeline Parameters:**
```python
snap_0 = Script(
    label='Process with Parameters',
    language='Python',
    script='''
# Access pipeline parameter (passed from parent)
threshold = $_thresholdValue

while self.input.hasNext():
    doc = self.input.next()
    if doc.get('value', 0) > threshold:
        self.output.write(doc, {"result": "pass", "original": doc})
    else:
        self.output.write(doc, {"result": "fail", "original": doc})
'''
)
```

#### Best Practices

1. **Document Justification**: If Script Snap is required, document WHY native Snaps cannot be used and list alternatives considered
2. **Documentation**: Document script logic comprehensively in Snap labels and pipeline docstrings
3. **Java Objects**: In JavaScript, use Java classes (HashMap, LinkedHashMap) for serializable objects

**Common Misuses to Avoid:**

**WRONG: Using Script Snap for simple transformation**
```python
# DON'T DO THIS
snap_0 = Script(
    language='Python',
    script='''
while self.input.hasNext():
    doc = self.input.next()
    doc['full_name'] = doc['first_name'] + ' ' + doc['last_name']
    doc['price_with_tax'] = doc['price'] * 1.1
    self.output.write({}, doc)
'''
)
```

**CORRECT: Use TransformMapper instead**
```python
snap_0 = TransformMapper(
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression="$first_name + ' ' + $last_name",
                target_path="$.full_name"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression="$price * 1.1",
                target_path="$.price_with_tax"
            )
        ]
    )
)
```

**Benefits of Native Snaps over Script Snap:**
- 10-50x better performance
- Better error handling and debugging
- Easier to test and maintain
- Version controlled configuration (not embedded code)
- Platform-optimized execution
- No Python 2.7.2 limitations

## 8. Expression Language Reference

The SnapLogic Expression Language is a powerful utility that allows you to use expressions (JavaScript syntax) to access functions and properties, set field values dynamically, and manipulate data within pipelines.

### Key Features

- **JavaScript-Based Syntax**: The expression language follows JavaScript syntax conventions
- **Dynamic Field Values**: Set field values dynamically based on input data
- **Data Manipulation**: Transform, filter, and process data inline
- **Function Callbacks**: Functions can be passed to other functions that accept callbacks (like `Array.map()` or `Array.filter()`)
- **Expression Libraries**: Create reusable expressions that can be imported into any pipeline

### Supported Operators

**Comparison Operators:**
- `>` (greater than)
- `>=` (greater than or equal)
- `<` (less than)
- `<=` (less than or equal)
- `==` (equals)
- `!=` (not equals)

> **Note:** Strict equals (`===`) and strict not equals (`!==`) are NOT supported.

**Logical Operators:**
- `&&` (AND)
- `||` (OR)
- `!` (NOT)

---

### Using Expressions

Expressions are available across multiple Snaps. If a Snap exposes expression functionality for a property, an icon (=) appears in front of the text box of the property. Only Snap properties in the Settings category can currently provide expression functionality.

#### Accessing Document Values

To access values in a document, you can use JavaScript object accessors:

```javascript
// Using dot notation
$first_name

// Underscore-prefixed fields: dot notation is supported and preferred
$._table
$.obj._field

// Using bracket notation (required for field names with spaces, dots, or hyphens)
$['field with spaces']
$['field-name']
$['field.name']

// Nested access
$customer.address.city

// Array access
$items[0].name
```

#### Expression Toggle

Any field preceded with an equal sign (=) button can handle an expression if that button is toggled on.

**Example Expression:**
```javascript
'/out' + Date.now() + '.json'
```
This would insert the current date as part of the filename.

#### Dynamic Validation

As you create expressions, they are validated in real-time for:
- Syntax errors
- Spelling errors
- Output previews

#### Using eval()

If you need to parameterize your pipeline with an expression, you can use the `eval()` function to evaluate an expression stored in a string:

```javascript
// Substitute Pipeline parameters
$.eval(_parameter)

// Execute functions
$.eval(Date.now())
```

The `$.eval()` function can be used without having to use an expression toggle (=).

#### Pipeline Parameters

Parameters are string values that allow a pipeline to be reused in multiple situations.

```javascript
// Prefix the parameter name with an underscore
_firstName
_lastName
_filePath
```

**Important Notes:**
- The value of a parameter is always a string
- You need to convert strings to numeric values before mathematical operations
- Simply adding two to a parameter will append the character "2"

**Converting String Parameters to Numbers:**
```javascript
// Wrong - will yield "122" instead of 14
_numValue + 2

// Correct - use parseInt or parseFloat
parseInt(_numValue) + 2
parseFloat(_numValue) + 2.5
```

#### Input Fields

Input view schema attributes can be used as part of expressions using the dollar sign (`$`) prefix:

```javascript
// Access fields from input document
$customer_id
$order_total
$['Home address']  // For fields with spaces or special characters
```

---

### JSONPath

JSONPath expressions let you specify the parts of a JSON document that are to be operated on by a Snap.

#### Basic Syntax

```javascript
// Reference the "name" field at the root
$.name

// Access nested objects
$.customer.address.city

// Array access
$.items[0]

// Wildcard - all items in array
$.items[*]
```

#### Path Expressions

| Expression | Description |
|------------|-------------|
| `$` | Root object/element |
| `@` | Current object/element |
| `.` or `[]` | Child operator |
| `..` | Recursive descent |
| `*` | Wildcard (all objects/elements) |
| `[]` | Subscript operator |
| `[,]` | Union operator |
| `[start:end:step]` | Array slice operator |
| `?()` | Filter expression |
| `()` | Script expression |

#### Recursive Descent (`$..`) and Filter Expressions

The recursive descent operator (`$..`) and filter expressions (`[?(expr)]`) are supported:

```javascript
// Recursive descent - find all 'name' fields at any depth
$..name

// Recursive descent with filter
$..[?(@.status == 'active')]

// Filter objects based on value
$.addresses[?(value.type == 'home')]

// Filter by numeric comparison
$.items[?(@.price > 100)]

// Filter by existence
$.items[?(@.discount)]
```

#### Extended JSONPath Methods

SnapLogic extends standard JSONPath syntax with method calls to manipulate query results:

```javascript
// Extract first element from filtered array
$.addresses[?(value.type == 'home')].first()

// Get array length (JSONPath syntax — in expressions, use .length without parentheses)
$.items.length()

// Map over results
$.items.map(item => item.name)
```

#### Mapping Root

The **Mapping Root** property in the Mapper Snap is a JSONPath that limits the scope of a mapping:

```javascript
// Iterate over objects in an array
$.my_array[*]
```

This enables the Mapper to iterate over the objects in the array and transform each object based on the mapping.

> **Important:** Expression language syntax and JSONPath syntax are not compatible. Simple syntax like `$.name` is valid in both, but anything non-trivial will likely not work.

---

### Global Functions and Properties

Global functions are available throughout the expression language without requiring a prefix.

#### Type Checking Functions

| Function | Description | Example |
|----------|-------------|---------|
| `typeof(value)` | Returns the type of value | `typeof($field)` -> `"string"` |
| `isNaN(value)` | Checks if value is NaN | `isNaN($amount)` |
| `isFinite(value)` | Checks if value is finite | `isFinite($number)` |

#### Parsing Functions

| Function | Description | Example |
|----------|-------------|---------|
| `parseInt(string, radix)` | Parse string to integer | `parseInt("42")` -> `42` |
| `parseFloat(string)` | Parse string to float | `parseFloat("3.14")` -> `3.14` |

#### URI Encoding Functions

| Function | Description | Example |
|----------|-------------|---------|
| `encodeURIComponent(str)` | Encodes a URI component | `encodeURIComponent("hello world")` |
| `decodeURIComponent(str)` | Decodes a URI component | `decodeURIComponent("hello%20world")` |
| `encodeURI(str)` | Encodes a complete URI | `encodeURI("http://example.com/path name")` |
| `decodeURI(str)` | Decodes a complete URI | `decodeURI("http://example.com/path%20name")` |

#### Other Global Functions

| Function | Description | Example |
|----------|-------------|---------|
| `eval(expression)` | Evaluates an expression string | `$.eval(_parameter)` |

---

### String Functions and Properties

String literals function similarly to JavaScript strings. A string literal can be constructed with either single quotes or double quotes.

**Note:** Template literals (backticks) are NOT supported in SnapLogic Expression Language. Use string concatenation with the `+` operator or `.concat()` method instead.

**Escape sequences in strings:** `\"`, `\'`, `\\`, `\n`, `\t`, `\xNN`, and `\uXXXX` all work in `.expr` files. For embedding quotes in `Expr("...")` inside Python pipeline files, use alternating quote styles (`Expr("field == 'value'")`), `\uXXXX` escapes (`\u0022` for `"`), or move complex string construction to an `.expr` library function.

#### String Properties

| Property | Description | Example |
|----------|-------------|---------|
| `.length` | Returns string length | `"hello".length` -> `5` |

#### String Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.charAt(index)` | Character at index | `"hello".charAt(0)` -> `"h"` |
| `.charCodeAt(index)` | Unicode value at index | `"A".charCodeAt(0)` -> `65` |
| `.concat(str1, str2, ...)` | Concatenate strings | `"Hello".concat(" ", "World")` |
| `.indexOf(searchValue)` | First index of value | `"hello".indexOf("l")` -> `2` |
| `.lastIndexOf(searchValue)` | Last index of value | `"hello".lastIndexOf("l")` -> `3` |
| `.localeCompare(str)` | Compare strings | `"a".localeCompare("b")` -> `-1` |
| `.match(regexp)` | Match against regex | `"test123".match(/\d+/)` |
| `.replace(search, replace)` | Replace occurrences | `"hello".replace("l", "L")` |
| `.search(regexp)` | Search for pattern | `"hello".search(/l/)` -> `2` |
| `.slice(start, end)` | Extract substring | `"hello".slice(1, 4)` -> `"ell"` |
| `.split(separator)` | Split into array | `"a,b,c".split(",")` -> `["a","b","c"]` |
| `.substring(start, end)` | Extract substring | `"hello".substring(1, 4)` -> `"ell"` |
| `.toLowerCase()` | Convert to lowercase | `"HELLO".toLowerCase()` -> `"hello"` |
| `.toUpperCase()` | Convert to uppercase | `"hello".toUpperCase()` -> `"HELLO"` |
| `.trim()` | Remove whitespace | `"  hello  ".trim()` -> `"hello"` |
| `.trimLeft()` | Trim leading whitespace | `"  hello".trimLeft()` |
| `.trimRight()` | Trim trailing whitespace | `"hello  ".trimRight()` |
| `.startsWith(searchStr)` | Check if starts with | `"hello".startsWith("he")` -> `true` |
| `.endsWith(searchStr)` | Check if ends with | `"hello".endsWith("lo")` -> `true` |
| `.contains(searchStr)` | Check if contains | `"hello".contains("ll")` -> `true` |
| `.sprintf(format, args...)` | Format string (printf-style) | `"%s has %d items".sprintf(name, count)` |
| `.lowerFirst()` | Lowercase first char | `"Hello".lowerFirst()` -> `"hello"` |
| `.upperFirst()` | Uppercase first char | `"hello".upperFirst()` -> `"Hello"` |
| `.camelCase()` | Convert to camelCase | `"foo_bar".camelCase()` -> `"fooBar"` |
| `.snakeCase()` | Convert to snake_case | `"fooBar".snakeCase()` -> `"foo_bar"` |
| `.kebabCase()` | Convert to kebab-case | `"fooBar".kebabCase()` -> `"foo-bar"` |
| `.repeat(count)` | Repeat string | `"ab".repeat(3)` -> `"ababab"` |
| `String.fromCharCode(code)` | Character from Unicode code point | `String.fromCharCode(34)` -> `"\""` |

---

### Number Functions and Properties

Number functions work similarly to JavaScript Number object methods.

| Method | Description | Example |
|--------|-------------|---------|
| `.toFixed(digits)` | Format with fixed decimals | `(3.14159).toFixed(2)` -> `"3.14"` |
| `.toExponential(digits)` | Format in exponential notation | `(12345).toExponential(2)` -> `"1.23e+4"` |
| `.toPrecision(precision)` | Format to precision | `(3.14159).toPrecision(3)` -> `"3.14"` |
| `.toString(radix)` | Convert to string | `(255).toString(16)` -> `"ff"` |

```javascript
// Fixed decimal places
$price.toFixed(2)  // "19.99"

// Scientific notation
$largeNumber.toExponential(3)  // "1.234e+6"

// Significant figures
$measurement.toPrecision(4)  // "12.34"
```

---

### Math Functions and Properties

Math functions provide mathematical operations and constants.

> **Note:** Not all supported methods may appear in the Functions and Properties drop-down list. If not available, you may type them in.

#### Math Constants

| Constant | Description | Value |
|----------|-------------|-------|
| `Math.E` | Euler's number | ~2.718 |
| `Math.LN2` | Natural log of 2 | ~0.693 |
| `Math.LN10` | Natural log of 10 | ~2.303 |
| `Math.LOG2E` | Base 2 log of E | ~1.443 |
| `Math.LOG10E` | Base 10 log of E | ~0.434 |
| `Math.PI` | Pi | ~3.14159 |
| `Math.SQRT1_2` | Square root of 1/2 | ~0.707 |
| `Math.SQRT2` | Square root of 2 | ~1.414 |

#### Basic Math Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.abs(x)` | Absolute value | `Math.abs(-5)` -> `5` |
| `Math.ceil(x)` | Round up | `Math.ceil(4.2)` -> `5` |
| `Math.floor(x)` | Round down | `Math.floor(4.8)` -> `4` |
| `Math.round(x)` | Round to nearest | `Math.round(4.5)` -> `5` |
| `Math.trunc(x)` | Truncate to integer | `Math.trunc(4.9)` -> `4` |
| `Math.sign(x)` | Sign of number | `Math.sign(-5)` -> `-1` |

#### Min/Max Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.max(a, b, ...)` | Maximum value | `Math.max(1, 5, 3)` -> `5` |
| `Math.min(a, b, ...)` | Minimum value | `Math.min(1, 5, 3)` -> `1` |

#### Power and Root Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.pow(base, exp)` | Power | `Math.pow(2, 3)` -> `8` |
| `Math.sqrt(x)` | Square root | `Math.sqrt(16)` -> `4` |
| `Math.cbrt(x)` | Cube root | `Math.cbrt(27)` -> `3` |
| `Math.exp(x)` | e^x | `Math.exp(1)` -> ~`2.718` |
| `Math.expm1(x)` | e^x - 1 | `Math.expm1(1)` -> ~`1.718` |
| `Math.hypot(a, b, ...)` | Hypotenuse | `Math.hypot(3, 4)` -> `5` |

#### Logarithmic Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.log(x)` | Natural log | `Math.log(Math.E)` -> `1` |
| `Math.log10(x)` | Base 10 log | `Math.log10(100)` -> `2` |
| `Math.log2(x)` | Base 2 log | `Math.log2(8)` -> `3` |
| `Math.log1p(x)` | log(1 + x) | `Math.log1p(1)` -> ~`0.693` |

#### Trigonometric Functions

| Function | Description |
|----------|-------------|
| `Math.sin(x)` | Sine (x in radians) |
| `Math.cos(x)` | Cosine |
| `Math.tan(x)` | Tangent |
| `Math.asin(x)` | Arcsine |
| `Math.acos(x)` | Arccosine |
| `Math.atan(x)` | Arctangent |
| `Math.atan2(y, x)` | Arctangent of y/x |
| `Math.sinh(x)` | Hyperbolic sine |
| `Math.cosh(x)` | Hyperbolic cosine |
| `Math.tanh(x)` | Hyperbolic tangent |

#### Random Number

| Function | Description | Example |
|----------|-------------|---------|
| `Math.random()` | Random number 0-1 | `Math.random()` -> `0.7234...` |

**Generate random integer in range:**
```javascript
// Random integer from 0 to max (exclusive)
Math.floor(Math.random() * max)

// Random integer from min to max (inclusive)
Math.floor(Math.random() * (max - min + 1)) + min
```

---

### Date Functions and Properties

Dates function similarly to JavaScript Date objects. A Date represents the number of milliseconds since midnight January 1, 1970 UTC.

**Important Notes:**
- Timestamp formats may differ across different databases or APIs
- Migrating date information may have unintended results if differences are not considered
- Time zone settings between Cloudplex and Groundplex might differ (Cloudplex may be in UTC, while Groundplex could be in local time zone)

#### Creating Dates

```javascript
// Current date/time
Date.now()
new Date()

// From timestamp (milliseconds)
new Date(1609459200000)

// From string
new Date("2021-01-01")
new Date("2021-01-01T12:00:00Z")

// From components (year, month, day, hour, minute, second, ms)
// Note: getMonth() is 1-indexed (1 = January); getMonthFromZero() is 0-indexed
new Date(2021, 0, 1, 12, 0, 0, 0)
```

#### Date Comparison

Dates can be compared using relational operators:
```javascript
date1 > date2
date1 >= date2
date1 < date2
date1 <= date2
date1 == date2
```

#### Date Get Methods (Local Time)

| Method | Description | Example |
|--------|-------------|---------|
| `.getFullYear()` | Get year (4 digits) | `date.getFullYear()` -> `2021` |
| `.getMonth()` | Get month (1-12) | `date.getMonth()` -> `1` (January) |
| `.getMonthFromZero()` | Get month (0-11, JS convention) | `date.getMonthFromZero()` -> `0` (January) |
| `.getDate()` | Get day of month (1-31) | `date.getDate()` -> `15` |
| `.getDay()` | Get day of week (0-6) | `date.getDay()` -> `0` (Sunday) |
| `.getHours()` | Get hours (0-23) | `date.getHours()` -> `14` |
| `.getMinutes()` | Get minutes (0-59) | `date.getMinutes()` -> `30` |
| `.getSeconds()` | Get seconds (0-59) | `date.getSeconds()` -> `45` |
| `.getMilliseconds()` | Get milliseconds (0-999) | `date.getMilliseconds()` |
| `.getTime()` | Get timestamp (ms since epoch) | `date.getTime()` |
| `.getTimezoneOffset()` | Get timezone offset (minutes) | `date.getTimezoneOffset()` |

#### Date Get Methods (UTC)

| Method | Description |
|--------|-------------|
| `.getUTCFullYear()` | Get UTC year |
| `.getUTCMonth()` | Get UTC month (1-12) |
| `.getUTCMonthFromZero()` | Get UTC month (0-11, JS convention) |
| `.getUTCDate()` | Get UTC day of month |
| `.getUTCDay()` | Get UTC day of week |
| `.getUTCHours()` | Get UTC hours |
| `.getUTCMinutes()` | Get UTC minutes |
| `.getUTCSeconds()` | Get UTC seconds |
| `.getUTCMilliseconds()` | Get UTC milliseconds |

#### Date Arithmetic Methods (Joda extensions — all return NEW Date)

Dates are **immutable**. These methods return a new Date; they do not modify the original.

| Method | Description | Example |
|--------|-------------|---------|
| `.plusDays(n)` | Add days | `date.plusDays(1)` |
| `.plusMonths(n)` | Add months | `date.plusMonths(3)` |
| `.plusYears(n)` | Add years | `date.plusYears(1)` |
| `.plusHours(n)` | Add hours | `date.plusHours(12)` |
| `.plusMinutes(n)` | Add minutes | `date.plusMinutes(30)` |
| `.plusSeconds(n)` | Add seconds | `date.plusSeconds(60)` |
| `.plusMillis(n)` | Add milliseconds | `date.plusMillis(500)` |
| `.plusWeeks(n)` | Add weeks | `date.plusWeeks(2)` |
| `.plus(ms)` | Add milliseconds (generic) | `date.plus(5000)` |
| `.minusDays(n)` | Subtract days | `date.minusDays(7)` |
| `.minusMonths(n)` | Subtract months | `date.minusMonths(1)` |
| `.minusYears(n)` | Subtract years | `date.minusYears(1)` |
| `.minusHours(n)` | Subtract hours | `date.minusHours(6)` |
| `.minusMinutes(n)` | Subtract minutes | `date.minusMinutes(15)` |
| `.minusSeconds(n)` | Subtract seconds | `date.minusSeconds(30)` |
| `.minusMillis(n)` | Subtract milliseconds | `date.minusMillis(100)` |
| `.minusWeeks(n)` | Subtract weeks | `date.minusWeeks(1)` |
| `.minus(ms)` | Subtract milliseconds (generic) | `date.minus(5000)` |

#### Date Field Replacement Methods (Joda extensions — all return NEW Date)

| Method | Description | Example |
|--------|-------------|---------|
| `.withYear(n)` | Set year | `date.withYear(2025)` |
| `.withMonthOfYear(n)` | Set month (1-12) | `date.withMonthOfYear(6)` |
| `.withDayOfMonth(n)` | Set day of month | `date.withDayOfMonth(1)` |
| `.withDayOfWeek(n)` | Set day of week (1=Mon, 7=Sun) | `date.withDayOfWeek(1)` |
| `.withDayOfYear(n)` | Set day of year | `date.withDayOfYear(1)` |
| `.withHourOfDay(n)` | Set hour | `date.withHourOfDay(9)` |
| `.withMinuteOfHour(n)` | Set minute | `date.withMinuteOfHour(0)` |
| `.withSecondOfMinute(n)` | Set second | `date.withSecondOfMinute(0)` |
| `.withMillisOfSecond(n)` | Set millisecond | `date.withMillisOfSecond(0)` |

#### Date Formatting Methods

| Method | Description | Example Output |
|--------|-------------|----------------|
| `.toLocaleDateString()` | Locale-specific date | `"1/1/2021"` |
| `.toLocaleTimeString()` | Locale-specific time | `"12:00:00 PM"` |
| `.toLocaleDateTimeString()` | Locale-specific date/time | `"1/1/2021, 12:00:00 PM"` |
| `.toString()` | ISO 8601 format (default) | `"2021-01-01T00:00:00.000Z"` |
| `.toString(format)` | Formatted with Java pattern | `toString("yyyy-MM-dd")` → `"2021-01-01"` |
| `.toLocaleString()` | Locale date + time | `"1/1/2021, 12:00:00 AM"` |

**Methods that do NOT exist** (common JS assumptions that fail in Tectonic):
`toISOString()`, `toDateString()`, `toTimeString()`, `toUTCString()`, `valueOf()`.
Use `.toString()` for ISO output or `.toString(format)` for custom formats.

#### Date Parsing

```javascript
// Parse date string
Date.parse("2021-01-01T12:00:00Z")  // Returns timestamp
```

The `toLocaleDateString()`, `toLocaleDateTimeString()`, and `toLocaleTimeString()` methods work with database types that are output as Joda DateTime objects.

---

### Array Functions and Properties

Array literals function similarly to JavaScript array literals.

> **Note:** Extra commas in array literals are NOT supported.

#### Creating Arrays

```javascript
// Array literal
[1, 2, 3]

// Mixed types
[1, "two", true, null]

// Nested arrays
[[1, 2], [3, 4]]

// Empty array
[]
```

#### Array Properties

| Property | Description | Example |
|----------|-------------|---------|
| `.length` | Number of elements | `[1, 2, 3].length` -> `3` |

#### Array Access Methods

| Method | Description | Example |
|--------|-------------|---------|
| `[index]` | Access by index | `arr[0]` |
| `.indexOf(item)` | Find first index | `[1,2,3].indexOf(2)` -> `1` |
| `.lastIndexOf(item)` | Find last index | `[1,2,1].lastIndexOf(1)` -> `2` |
| `.find(fn)` | Find first matching | `arr.find(x => x > 2)` |
| `.findIndex(fn)` | Find index of first matching | `arr.findIndex(x => x > 2)` |

#### Array Transformation Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.map(fn)` | Transform each element | `[1,2,3].map(x => x * 2)` -> `[2,4,6]` |
| `.filter(fn)` | Filter elements | `[1,2,3].filter(x => x > 1)` -> `[2,3]` |
| `.reduce(fn, init)` | Reduce to single value | `[1,2,3].reduce((a,b) => a+b, 0)` -> `6` |
| `.reduceRight(fn, init)` | Reduce from right | `[1,2,3].reduceRight((a,b) => a+b, 0)` |

#### Array Modification Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.concat(arr2)` | Concatenate arrays | `[1,2].concat([3,4])` -> `[1,2,3,4]` |
| `.slice(start, end)` | Extract portion | `[1,2,3,4].slice(1,3)` -> `[2,3]` |
| `.splice(start, count, items...)` | Add/remove elements | `arr.splice(1, 2, 'a', 'b')` |
| `.push(item)` | Add to end | `arr.push(4)` |
| `.pop()` | Remove from end | `arr.pop()` |
| `.shift()` | Remove from start | `arr.shift()` |
| `.unshift(item)` | Add to start | `arr.unshift(0)` |
| `.reverse()` | Reverse in place | `[1,2,3].reverse()` -> `[3,2,1]` |
| `.sort(fn)` | Sort in place | `[3,1,2].sort()` -> `[1,2,3]` |


#### Array Joining

| Method | Description | Example |
|--------|-------------|---------|
| `.join(separator)` | Join to string | `[1,2,3].join('-')` -> `"1-2-3"` |
| `.toString()` | Convert to string | `[1,2,3].toString()` -> `"1,2,3"` |

---

### Object Functions and Properties

Object literals allow you to construct an object with a set of properties.

#### Creating Objects

```javascript
// Object literal
{ name: "John", age: 30 }

// Nested objects
{
  person: { name: "John" },
  items: [1, 2, 3]
}

// Computed property names
{ [dynamicKey]: value }
```

#### Object Static Methods

| Method | Description | Example |
|--------|-------------|---------|
| `Object.keys(obj)` | Get array of keys | `Object.keys({a:1, b:2})` -> `["a","b"]` |
| `Object.values(obj)` | Get array of values | `Object.values({a:1, b:2})` -> `[1,2]` |
| `Object.entries(obj)` | Get array of [key, value] | `Object.entries({a:1})` -> `[["a",1]]` |

#### Object Instance Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.hasOwnProperty(key)` | Check if has property | `obj.hasOwnProperty("name")` |
| `.hasPath(key)` | Check path exists with non-null value | `obj.hasPath("address.city")` |
| `.isEmpty()` | Check if no properties | `{}.isEmpty()` -> `true` |
| `.extend(obj1, obj2, ...)` | Merge objects into copy (non-mutating) | `$obj.extend({"status": "active"})` |
| `.get(key, default?)` | Get value with optional default | `$obj.get("email", "unknown")` |
| `.getFirst(key, default?)` | Get first element if value is list | `$obj.getFirst("tags", "none")` |
| `.merge(other)` | Merge another object | `$obj.merge($overlay)` |
| `.filter(fn)` | Filter entries by predicate (v, k, obj) | `$obj.filter((v, k) => v != null)` |
| `.mapKeys(fn)` | Transform keys (v, k, obj) | `$obj.mapKeys((v, k) => k.toUpperCase())` |
| `.mapValues(fn)` | Transform values (v, k, obj) | `$obj.mapValues(v => v * 2)` |
| `.toString()` | Convert to string | `$obj.toString()` |

#### Spread Operator

A JSON Array of objects with unique/non-overlapping keys can be converted to an object using the extend object method along with a Spread Operator:

```javascript
// Merge objects
{ ...$obj1, ...$obj2 }

// Merge using extend
{}.extend($obj1, $obj2)
```

#### Converting Array to Object

```javascript
// Using spread to merge array of objects
{ ...$array[0], ...$array[1], ...$array[2] }

// Using extend with list of [key, value] pairs
{}.extend([["a", 1], ["b", 2], ["c", 3]])
// Result: {a: 1, b: 2, c: 3}
```

---

### JSON Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `JSON.parse(string)` | Parse JSON string to object | `JSON.parse('{"a":1}')` -> `{a: 1}` |
| `JSON.stringify(obj)` | Convert object to JSON string | `JSON.stringify({a: 1})` -> `'{"a":1}'` |
| `JSON.stringify(obj, null, indent)` | Pretty print with indentation | `JSON.stringify(obj, null, 2)` |

```javascript
// Parse JSON string
let data = JSON.parse($jsonString)

// Stringify with formatting
JSON.stringify($object, null, 2)

// Access parsed data
JSON.parse($jsonField).propertyName
```

---

### Base64 Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `Base64.encode(string)` | Encode string to Base64 | `Base64.encode("Hello")` -> `"SGVsbG8="` |
| `Base64.decode(string)` | Decode Base64 to string | `Base64.decode("SGVsbG8=")` -> `"Hello"` |
| `Base64.encodeAsBinary(data)` | Encode to Base64 as bytes | `Base64.encodeAsBinary(byteArray)` |
| `Base64.decodeAsBinary(string)` | Decode Base64 to bytes | `Base64.decodeAsBinary("SGVsbG8=")` |
| `Base64.decodeGZip(string)` | Decode Base64 and decompress gzip | `Base64.decodeGZip(encoded)` |
| `Base64.decodeGZipAsBinary(string)` | Decode Base64 and decompress to bytes | `Base64.decodeGZipAsBinary(encoded)` |

Use Cases: encoding binary data for transmission, encoding credentials for Basic Authentication, encoding file contents.

---

### Digest Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `Digest.md5(string)` | MD5 hash | `Digest.md5("alpha")` -> `"2c1743a391305fbf367df8e4f069f9f9"` |
| `Digest.sha1(string)` | SHA-1 hash | `Digest.sha1("alpha")` |
| `Digest.sha256(string)` | SHA-256 hash | `Digest.sha256("alpha")` |
| `Digest.sha512(string)` | SHA-512 hash | `Digest.sha512("alpha")` |

Use Cases: creating checksums, password hashing (use SHA-256 or better for security), data integrity verification.

---

### GZip Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `GZip.compress(data)` | Compress data | `GZip.compress("Hello World")` |
| `GZip.decompress(data)` | Decompress data | `GZip.decompress(compressedData)` |
Use Cases: reducing payload size for API calls, compressing large text data, working with compressed file formats.

> For Base64+GZip patterns, use: `Base64.encode(GZip.compress(data))` to compress and encode, `Base64.decodeGZip(encoded)` to decode and decompress.

---

### iconv - Encode and Decode Functions

Supported encoding types: UTF-8, UTF-16, UTF-32.

| Method | Description | Example |
|--------|-------------|---------|
| `iconv.encode(string, encoding)` | Encode to specified encoding | `iconv.encode("Hello", "UTF-16")` |
| `iconv.decode(bytes, encoding)` | Decode from specified encoding | `iconv.decode(data, "UTF-8")` |

---

### HTML - Encode and Decode Functions

| Method | Description | Example |
|--------|-------------|---------|
| `HTML.encode(string)` | Encode to HTML entities | `HTML.encode("<div>")` -> `"&lt;div&gt;"` |
| `HTML.decode(string)` | Decode HTML entities | `HTML.decode("&lt;div&gt;")` -> `"<div>"` |

**Common HTML Entities:**

| Character | Entity |
|-----------|--------|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |
| `"` | `&quot;` |
| `'` | `&#39;` |

---

### Pipeline Functions and Properties

| Property | Description | Example |
|----------|-------------|---------|
| `pipe.label` | Pipeline label/name | `pipe.label` -> `"My Pipeline"` |
| `pipe.ruuid` | Runtime UUID | `pipe.ruuid` -> `"abc123..."` |
| `pipe.args` | Map of pipeline parameters | `pipe.args['paramName']` |
| `pipe.plexPath` | Snaplex path | `pipe.plexPath` |
| `pipe.projectPath` | Project path | `pipe.projectPath` |

#### Accessing Pipeline Parameters

```javascript
// Direct parameter access
_parameterName

// Through pipe.args
pipe.args['parameterName']
pipe.args.parameterName
```

#### Generating Unique IDs

Use `pipe.ruuid` to generate unique identifiers for pipeline runs:

```javascript
// Create unique filename
"output_" + pipe.ruuid + ".json"
```

---

### Snap Functions and Properties

| Property | Description | Example |
|----------|-------------|---------|
| `snap.label` | Snap label | `snap.label` -> `"Mapper (Data)"` |
| `snap.instanceId` | Snap instance ID | `snap.instanceId` |

```javascript
// Include snap label in error messages
"Error in " + snap.label + ": " + $errorMessage

// Create snap-specific identifiers
snap.label + "_" + Date.now()
```

---

### Task Properties and Functions

| Property | Description | Example |
|----------|-------------|---------|
| `task.label` | Task label | `task.label` -> `"My Triggered Task"` |
| `task.ruuid` | Task Runtime UUID | `task.ruuid` |

When working with enterprise schedulers, you can use `pipe.ruuid` in a Mapper Snap to return the Runtime ID when the Triggered Task runs:

```javascript
// In Mapper expression
{
  "ruuid": pipe.ruuid
}
```

---

### SL Functions and Properties

SL (SnapLogic) functions provide SnapLogic-specific utilities.

| Function | Description | Example |
|----------|-------------|---------|
| `sl.ensureArray(value)` | Ensure value is array | `sl.ensureArray([1,2,3])` -> `[1,2,3]` |
| `sl.ensureArray(value)` | Wrap non-array in array | `sl.ensureArray("x")` -> `["x"]` |
| `sl.gethostbyname(hostname)` | Get IP address | `sl.gethostbyname("www.snaplogic.com")` |
| `sl.range(start, end, step)` | Generate number range | `sl.range(0, 5, 1)` -> `[0,1,2,3,4]` |
| `sl.zip(arr1, arr2)` | Zip arrays together | `sl.zip([1,2], ["a","b"])` -> `[[1,"a"],[2,"b"]]` |
| `sl.zipObject(keys, values)` | Create object from arrays | `sl.zipObject(["a","b"], [1,2])` -> `{a:1, b:2}` |

#### sl.ensureArray Examples

```javascript
// Already an array - returns as-is
sl.ensureArray([1, 2, 3])  // [1, 2, 3]

// Single value - wraps in array
sl.ensureArray("single")   // ["single"]

// Null/undefined handling
sl.ensureArray(null)       // [null] or []
```

#### sl.range Examples

```javascript
// Generate sequence
sl.range(1, 6, 1)   // [1, 2, 3, 4, 5]
sl.range(0, 10, 2)  // [0, 2, 4, 6, 8]
```

---

### The match Control Operator

The `match` operator allows you to choose an expression to be executed based on whether an input value matches a given pattern. It is useful when you need to execute different expressions based on complex conditions.

#### Syntax

```javascript
match (inputValue) {
  pattern1 => expression1,
  pattern2 => expression2,
  _ => defaultExpression
}
```

#### Examples

```javascript
// Match on string values
match ($status) {
  "active" => "Account is active",
  "pending" => "Account is pending approval",
  "suspended" => "Account has been suspended",
  _ => "Unknown status"
}

// Match with conditions
match ($score) {
  x if x >= 90 => "A",
  x if x >= 80 => "B",
  x if x >= 70 => "C",
  x if x >= 60 => "D",
  _ => "F"
}
```

Use Cases: status code translation, category assignment, conditional transformations, switch-case style logic.

---

### Expression Language Examples

#### Conditional Expressions

```javascript
// Ternary operator
$age >= 18 ? "Adult" : "Minor"

// Nested ternary (each else-branch parenthesized — see Gotcha 1)
$score >= 90 ? "A" : ($score >= 80 ? "B" : ($score >= 70 ? "C" : "D"))

// Null coalescing
$value || "default"
$name != null ? $name : "Unknown"
```

#### String Examples

**Checking for Non-empty String:**
```javascript
$field != null && $field.length > 0
$field != null && $field.trim() != ""
```

**Checking for Existing Value:**
```javascript
$field != null
typeof($field) != "undefined"
```

**Creating Email from Name:**
```javascript
$firstName.charAt(0).toLowerCase() + $lastName.toLowerCase() + "@company.com"
```

#### Date Examples

**Creating and Formatting a Date in Specific Timezone:**
```javascript
new Date().toLocaleDateString("en-US", {timeZone: "America/New_York"})
```

**Formatting Date with Letters:**
```javascript
new Date().toLocaleDateString("en-US", {month: "long", day: "numeric", year: "numeric"})
// "January 15, 2021"
```

**Creating ISO-formatted Date:**
```javascript
Date.now().toString()
// "2021-01-15T12:00:00.000Z"
```

**Parsing a Date:**
```javascript
new Date(Date.parse($dateString))
Date.parse("2021-01-15")
```

**Parsing Non-standard Date:**
```javascript
// For "15/01/2021" format (DD/MM/YYYY)
let parts = $dateString.split("/");
new Date(parts[2], parts[1] - 1, parts[0])
```

**Current Month Name:**
```javascript
new Date().toLocaleDateString("en-US", {month: "long"})
// "January"
```

#### Filtering Examples

**Filtering for Two Possible Values:**
```javascript
$items.filter(item => item.status == "active" || item.status == "pending")
```

**Filtering by Multiple Fields:**
```javascript
$items.filter(item => item.category == "A" && item.price > 100)
```

**Filtering by Date within Timeframe:**
```javascript
let now = Date.now();
let oneWeekAgo = now - (7 * 24 * 60 * 60 * 1000);
$items.filter(item => Date.parse(item.date) >= oneWeekAgo)
```

#### Object Manipulation Examples

**Merging Objects:**
```javascript
{}.extend($obj1, $obj2)
{ ...$obj1, ...$obj2 }
```

**Extracting Specific Fields:**
```javascript
{
  id: $source.id,
  name: $source.name,
  email: $source.contact.email
}
```

**Creating Object from Arrays:**
```javascript
sl.zipObject($keys, $values)
```

#### Array Transformation Examples

**Mapping to Extract Field:**
```javascript
$users.map(user => user.email)
```

**Calculating Sum:**
```javascript
$numbers.reduce((sum, n) => sum + n, 0)
```

**Finding Maximum:**
```javascript
$numbers.reduce((max, n) => n > max ? n : max, $numbers[0])
Math.max(...$numbers)
```

**Grouping by Property:**
```javascript
$items.reduce((groups, item) => {
  let key = item.category;
  groups[key] = groups[key] || [];
  groups[key].push(item);
  return groups;
}, {})
```

---

### Quick Reference Tables

#### Common Patterns

| Task | Expression |
|------|------------|
| Check if null | `$field != null` |
| Default value | `$field \|\| "default"` |
| String to number | `parseInt($field)` or `parseFloat($field)` |
| Number to string | `$field.toString()` |
| Current timestamp | `Date.now()` |
| Current date (ISO) | `Date.now().toString()` |
| Array length | `$array.length` |
| First element | `$array[0]` |
| Last element | `$array[$array.length - 1]` |
| Unique values | `[...new Set($array)]` |
| Sort ascending | `$array.sort((a,b) => a - b)` |
| Sort descending | `$array.sort((a,b) => b - a)` |

#### Useful Conversions

| From | To | Expression |
|------|----|------------|
| String | Integer | `parseInt($str)` |
| String | Float | `parseFloat($str)` |
| Number | String | `$num.toString()` |
| Array | String | `$arr.join(",")` |
| String | Array | `$str.split(",")` |
| Object | JSON String | `JSON.stringify($obj)` |
| JSON String | Object | `JSON.parse($str)` |
| Date | Timestamp | `$date.getTime()` |
| Timestamp | Date | `new Date($timestamp)` |

---

## 9. Expression Libraries (.expr)

Expression libraries are files (`.expr`) that contain reusable expressions and functions importable into a Pipeline for use across all expression properties.

### Restrictions

Expression libraries (.expr files) are NOT full JavaScript. They are LIMITED to single-expression arrow functions. Verify against every item in this list before generating or validating an expression library.

**FORBIDDEN Constructs:**

- **NO braces `{}`** after arrow `=>`
- **NO `return` keyword** anywhere
- **NO `if/else` statements** -- use ternary `? :` instead
- **NO `for`, `while`, or any loops** -- use `.map()`, `.filter()`, `.reduce()` instead
- **NO `const`, `let`, `var`** -- single expression only
- **NO `class` definitions**
- **NO `function` keyword**
- **NO `===` or `!==`** -- use `==` and `!=` instead
- **NO bare nested ternaries** — `a ? b : c ? d : e` is a parse error. ALWAYS wrap each else-branch: `a ? b : (c ? d : e)`. See Gotcha 1
- **NO `++`, `--`, `+=`, `-=`, `*=`, `/=`** -- not supported
- **NO `this.otherFunction()` cross-references** -- `this.fn()` returns null in `slpy exec`. Use `lib.<name>.fn()` for cross-references between library functions, or inline the logic.
- **NO comments** (`/* */` or `//`) in `.expr` files -- the parser tokenizes them as expressions, causing `Unexpected token` errors or silent truncation
- **NO `String()`, `Number()`, `Boolean()` constructors** -- silently return null (not supported on platform either). Use `'' + expr` for string coercion, `parseFloat(x)` / `parseInt(x)` for number coercion, `x == 'true'` for boolean coercion
- **NO IIFE** `(function() { ... })()` -- parse error. Inline the logic as a single arrow expression
- **NO object literal `{...}` as root of `Expr()`** -- returns null. Use individual `target_path` mappings in TransformMapper instead
- **NO `btoa()` or `atob()`** -- browser APIs, not supported. Use `Base64.encode(str)` / `Base64.decode(str)` instead
- **NO `$$` prefix** (e.g., `$$parent.field`) -- parent scope does not exist in SnapLogic expressions. Use `pass_through=True` + explicit field mapping
- **NO `.length()`** -- `.length` is a property, not a method. Use `$arr.length`, not `$arr.length()`
- **NO `$dict[$key]` inside `.filter()` or `.map()` callbacks** -- document-level variable references inside callbacks silently return null. Use nested `.filter()` for cross-array lookups instead

**ALLOWED Only:**

- Object literals with key-value pairs
- Single-expression arrow functions: `param => expression`
- Ternary operators: `condition ? value1 : value2`
- Nested ternaries for complex logic (wrapped in parentheses)
- Method chaining: `.map().filter().reduce()`
- Arithmetic and logical operators: `+, -, *, /, ==, !=, &&, ||`
- Built-in functions: `Math.*`, `Date.now().toString()`, `Date.now().toString("yyyy-MM-dd")`, `Date.parse(str, format)`, etc.
- String coercion via concatenation: `'' + expr`
- Spread/rest parameters: `(x, y, ...other) => expression`
- Default parameters: `(param = defaultValue) => expression`

---

### File Structure and Syntax

An expression library file contains a single top-level JavaScript object literal. This object can have multiple child objects, functions, and values:

```javascript
{
  propertyName: "value",
  numericValue: 42,

  myFunction: x => x * 2,

  add: (a, b) => a + b,

  config: {
    prefix: "PRE_",
    suffix: "_SUF"
  }
}
```

**Key rules:**
- The file is a single top-level `{ ... }` object
- Properties are key-value pairs separated by commas
- Functions are single-expression arrow functions
- Values are STATIC and cannot be changed during Pipeline execution
- When a Pipeline executes, library contents are evaluated and stored as properties in the `lib` global variable

---

### Arrow Function Rules

Only SINGLE-EXPRESSION arrow functions are supported. The expression is evaluated and returned automatically -- NO braces, NO return statement.

```javascript
// Multiple parameters - single expression
(param1, param2, paramN) => expression

// Single parameter (parentheses optional) - single expression
param => expression

// No parameters (parentheses required) - single expression
() => expression

// Default parameters - single expression
(param = defaultValue) => expression

// Rest parameters (spread operator) - single expression
(x, y, ...other) => other.reduce((a, b) => a + b, x + y)
```

**How to handle complex logic WITHOUT if/else or braces:**

Use nested ternaries:
```javascript
result: (x) => condition1 ? value1 : (condition2 ? value2 : (condition3 ? value3 : defaultValue))
```

Use logical operators for short-circuits:
```javascript
safe_operation: x => x && x.property || 'default'
```

Use method chaining:
```javascript
process_data: data => data.filter(x => x.active).map(x => x.value).reduce((a, b) => a + b, 0)
```

---

### Built-in Variables

The following variables are available within expression library code:

| Variable | Description |
|----------|-------------|
| `this` | References the library object being constructed. On the SnapLogic platform, `this.` can reference other functions/values. However, **`this.functionName()` silently returns null in `slpy exec`**. Use `lib.<name>.fn()` instead for cross-references -- this works in both `slpy exec` and platform. |
| `__path__` | The path to this library as listed in the Pipeline imports |
| `__name__` | The name of this library (derived or specified in imports) |

Example using `this` (platform-only -- inline for slpy exec):
```javascript
{
  base_url: "https://api.example.com",
  get_endpoint: path => "https://api.example.com" + path
}
```

---

### Importing in Pipelines

Before using expression libraries in Snaps, import them in the pipeline definition:

```python
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries

p = Pipeline(label='Pipeline with Expression Libraries')

# Import expression libraries
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/dates.expr',    # Path to .expr file
        as_='dates'                       # Alias for use in expressions
    ),
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/validation.expr',
        as_='validation'
    ),
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/formatting.expr',
        as_='fmt'
    )
])
```

**IMPORTANT**: The `as_` field defines the library name used in expressions. Always use the alias (not the path) when referencing library functions.

**CORRECT:**
```python
expression=Expr("lib.dates.prev_month_start(Date.now())")  # Uses 'dates' alias
```

**WRONG:**
```python
expression=Expr("lib.shared/lib/dates.prev_month_start(Date.now())")  # Path not allowed
```

---

### Using in Snaps

Expression libraries are referenced using the pattern: `lib.{alias}.{function_name}(parameters)`

Example usage in TransformMapper:
```python
snap_0 = TransformMapper(
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.dates.prev_month_start($.orderDate)',
                target_path='$.previousMonthStart'
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.utils.calculate_discount($.price, $.customerTier)',
                target_path='$.discountedPrice'
            )
        ],
        mapping_root='$'
    )
)
```

---

### Library Overlays

You can overlay values from one library over another by giving them the same name in the "As" column of the Expression Libraries table. This allows you to create libraries with default values that can be specialized.

**Base library (`config_defaults.expr`):**
```javascript
{
  apiUrl: "https://api.example.com",
  timeout: 30000,
  retryCount: 3
}
```

**Override library (`config_prod.expr`), imported with same name:**
```javascript
{
  apiUrl: "https://api.production.example.com",
  timeout: 60000
}
```

When both are imported with the same "As" name, the values merge like `.extend()`, with later imports overriding earlier ones:

```javascript
lib.config.apiUrl      // "https://api.production.example.com" (overridden)
lib.config.timeout     // 60000 (overridden)
lib.config.retryCount  // 3 (preserved from base)
```

**In SLPy:**
```python
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/config_defaults.expr',
        as_='config'
    ),
    ExpressionLibraries.ExpressionLibraryItem(
        path='shared/lib/config_prod.expr',
        as_='config'  # Same alias -- values merge
    )
])
```

---

### Examples

#### Example: Simple Helpers

```javascript
{
  prefix: 'test',
  prefixer: x => 'test' + x
}
```
Usage: `lib.helpers.prefixer('value')` returns `'testvalue'`

> **Note:** `this.prefix` works on the SnapLogic platform but silently returns null in `slpy exec`. Inline the value for compatibility.

#### Example: Spread Operator (Variable Parameters)

```javascript
{
  CONCAT: (x, y, ...other) => other.reduce((accum, curVal) => accum + curVal, x.toString() + y.toString())
}
```
Usage: `lib.utils.CONCAT('a', 'b', 'c', 'd')` returns `'abcd'`

#### Example: Status Mapping (Real-World)

```javascript
{
  typeMap: {
    Checking: "CHK",
    Savings: "SAV",
    "Home Loan": "MOR"
  },

  convertStatus: x => (x == "Done" ? "COMPLETED" : (x.indexOf("error") != -1 ? "ERROR" : "UNKNOWN"))
}
```
Usage in Mapper:
- `lib.demo.convertStatus($status)` -> Target: `$updated_status`
- `lib.demo.typeMap[$type]` -> Target: `$updated_type`

#### Example: Date Utilities Library

```javascript
{
  get_today: () => Date.now().toString("yyyy-MM-dd"),

  get_timestamp: () => Date.now().toString("yyyyMMdd'T'HHmmss"),

  get_compact_timestamp: () => Date.now().toString("yyyyMMddHHmmss"),

  toMonthDate: (x) => x.withDayOfMonth(1),

  prevMonthStart: (x) => (x != null ? x : Date.now()).minusMonths(1).withDayOfMonth(1),

  prevMonthEnd: (x) => (x != null ? x : Date.now()).withDayOfMonth(1).minusDays(1),

  prevMonthStartString: (x) => (x != null ? x : Date.now()).minusMonths(1).withDayOfMonth(1).toString("yyyy-MM-dd"),

  prevMonthEndString: (x) => (x != null ? x : Date.now()).withDayOfMonth(1).minusDays(1).toString("yyyy-MM-dd"),

  firstDayOfMonth: (date) => date.withDayOfMonth(1),

  lastDayOfMonth: (date) => date.plusMonths(1).withDayOfMonth(1).minusDays(1),

  toEpoch: (date) => Math.floor(date.getTime() / 1000),

  fromEpoch: (seconds) => new Date(seconds * 1000)
}
```

**Usage in Pipeline:**
```javascript
lib.date_utils.get_today()                 // "2026-01-15"
lib.date_utils.get_timestamp()             // "20260115T143522"
lib.date_utils.prevMonthStartString()      // "2025-12-01"
lib.date_utils.toEpoch(new Date())         // 1704067200
```

#### Example: String Utilities Library

```javascript
{
  padZeros: (num, length) => ('000000' + num).slice(-length),

  toTitleCase: (str) => str.replace(/\w\S*/g, txt =>
    txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
  ),

  removeWhitespace: (str) => str.replace(/\s/g, ''),

  truncate: (str, maxLength) =>
    str.length > maxLength ? str.substring(0, maxLength - 3) + '...' : str,

  toSlug: (str) => str.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, ''),

  isBlank: (str) => !str || str.trim().length == 0,

  safe: (str) => (str != null ? str : '')
}
```

> **Note:** Use `==` not `===`. Use `(str != null ? str : '')` instead of `str || ''` for null safety.

#### Example: Validation Library

```javascript
{
  isValidEmail: (email) => email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/) != null,

  isNonEmpty: (value) => value != null && ('' + value).trim().length > 0,

  isNumeric: (value) => !isNaN(parseFloat(value)) && isFinite(value),

  isInteger: (value) => Number.isInteger(Number(value)),

  inRange: (value, min, max) =>
    !isNaN(parseFloat(value)) && parseFloat(value) >= min && parseFloat(value) <= max,

  hasLength: (str, min, max) =>
    ((str != null ? str : '').length >= min) && (max == undefined || (str != null ? str : '').length <= max),

  isOneOf: (value, allowedValues) => allowedValues.indexOf(value) != -1
}
```

> **Note:** Regex literals work inside function bodies but NOT as bare constants (causes loader hang). Use `str.match(/pattern/) != null` — never `/pattern/.test(str)` (`.test()` throws `UnknownMethodException`).

#### Example: Configuration Library

Expression libraries are excellent for storing configuration and metadata:

```javascript
{
  environment: "production",

  endpoints: {
    users: "/api/v1/users",
    orders: "/api/v1/orders",
    products: "/api/v1/products"
  },

  defaults: {
    pageSize: 50,
    timeout: 30000,
    retryCount: 3
  },

  statusCodes: {
    ACTIVE: 1,
    INACTIVE: 0,
    PENDING: 2,
    DELETED: -1
  },

  getStatusName: code => (code == 1 ? 'ACTIVE' : (code == 0 ? 'INACTIVE' : (code == 2 ? 'PENDING' : (code == -1 ? 'DELETED' : 'UNKNOWN')))),

  buildUrl: (endpoint) => "/api/v1/" + endpoint
}
```

> **Note:** No comments, no `this.` cross-references, no braces/return/let/if, and no `===`. Configuration values (nested objects) work fine; only function patterns are restricted.

#### Example: Type Checking

```javascript
{
  is_array: val => val instanceof Array,
  is_string: val => typeof val == "string",
  has_property: (obj, prop) => prop in obj,

  safe_get: (arr, index) => (arr instanceof Array && index in arr) ? arr[index] : null
}
```

#### Example: Comprehensive Pipeline Library Template

```javascript
{
  tax_rate: 0.08,
  max_discount: 0.30,
  default_currency: 'USD',

  get_today: () => Date.now().toString("yyyy-MM-dd"),
  get_today_iso: () => Date.now().toString("yyyy-MM-dd"),
  get_timestamp: () => Date.now().toString("yyyyMMdd'T'HHmmss"),

  format_phone: (phone) => phone.replace(/[^0-9]/g, ''),
  format_currency: (amount) => '$' + amount.toFixed(2),
  format_full_name: (first, last) => (first + ' ' + last).trim().toUpperCase(),

  calculate_discount: (tier, amount) =>
    (tier == 'platinum' ? amount * 0.80 :
    (tier == 'gold' ? amount * 0.85 :
    (tier == 'silver' ? amount * 0.90 :
    (tier == 'bronze' ? amount * 0.95 :
    amount)))),

  categorize_score: (score) =>
    (score >= 90 ? 'A' :
    (score >= 80 ? 'B' :
    (score >= 70 ? 'C' :
    (score >= 60 ? 'D' :
    'F')))),

  is_valid_email: (email) => email.contains('@') && email.contains('.'),
  is_valid_zip: (zip) => zip.match(/^\d{5}(-\d{4})?$/) != null,

  sum_amounts: (items) => items.map(i => i.amount).reduce((a, b) => a + b, 0),
  filter_active: (users) => users.filter(u => u.status == 'active'),
  extract_ids: (records) => records.map(r => r.id),

  truncate: (str, len) => str.length > len ? str.substring(0, len) + '...' : str,
  capitalize: (str) => str.charAt(0).toUpperCase() + str.slice(1).toLowerCase(),

  safe_string: (value) => (value != null ? value : ""),
  to_csv_field: (value) => (value == null || value == undefined || value + "" == "null") ? "" : value + "",
  format_number: (numStr) => ('' + (parseFloat(numStr) / 1000)),

  get_api_url: (host) => "https://" + host + "/api/v1"
}
```

---

### Validation Checklist

Before generating or editing an expression library, verify every item in the **Restrictions** section above (FORBIDDEN Constructs + ALLOWED Only). Additionally check:
- [ ] **NO self-referencing in TransformMapper** -- if `$field` is a `target_path` in the same mapper AND is not in the input, split into sequential mappers (Gotcha 12)

#### Date Formatting Patterns

```javascript
// yyyy-MM-dd (e.g., "2026-01-15")
get_date: () => Date.now().toString("yyyy-MM-dd")

// yyyyMMdd'T'HHmmss (e.g., "20260115T143522") — quoted 'T' produces literal T
get_timestamp: () => Date.now().toString("yyyyMMdd'T'HHmmss")

// yyyyMMddHHmmss (e.g., "20260115143522")
get_compact_timestamp: () => Date.now().toString("yyyyMMddHHmmss")

// Dynamic filename with date
make_filename: (prefix) => prefix + Date.now().toString("yyyyMMdd'T'HHmmss") + ".csv"
```

`Date.parse(dateStr, format)` also supports a 2-arg signature with Java-style format patterns for parsing non-standard date strings.

#### Null-Safe Patterns

```javascript
// String coercion (NEVER use String(), Number(), Boolean() constructors)
format_value: (numStr) => ('' + (parseFloat(numStr) / 1000))

// Null-safe value access
safe_string: (value) => (value != null ? value : "")

// Triple null check for CSV fields
to_csv_field: (value) => (value == null || value == undefined || value + "" == "null") ? "" : value + ""

// Cross-array lookup (NOT dictionary access in callbacks)
// WRONG: $source.map(r => $lookup[$r.key])  -- $lookup returns null in callback
// CORRECT: Use nested .filter()
// $source.filter(r => $target.filter(t => t.key == r.key).length > 0)
```

#### Quick Validation Examples

**Wrong -> Correct conversions:**

```javascript
// WRONG: Multi-line function
calc: (x, y) => {
  const sum = x + y;
  return sum * 2;
}
// CORRECT: Single expression
calc: (x, y) => (x + y) * 2

// WRONG: if/else
categorize: (n) => {
  if (n >= 90) return 'A';
  else if (n >= 80) return 'B';
  else return 'C';
}
// CORRECT: Nested ternary with parentheses
categorize: (n) => n >= 90 ? 'A' : (n >= 80 ? 'B' : 'C')

// WRONG: for loop
sum: (arr) => {
  let total = 0;
  for (let i = 0; i < arr.length; i++) {
    total += arr[i];
  }
  return total;
}
// CORRECT: reduce
sum: (arr) => arr.reduce((acc, val) => acc + val, 0)

// WRONG: strict equality
isActive: (status) => status === 'active'
// CORRECT: loose equality
isActive: (status) => status == 'active'
```

## 10. Generation Templates

### Complete Pipeline Structure Template

```python
"""
Pipeline Name: {Descriptive Pipeline Name}

Pipeline Summary:
{2-3 sentence description of what this pipeline does, data sources,
transformations, and destinations}

{Optional Script Snap Warning if applicable - see Checkpoint 3}

Snap Inventory:
(#snap_0) {SnapName}: {Brief description of snap purpose and key configuration}
(#snap_1) {SnapName}: {Brief description of snap purpose and key configuration}
(#snap_2) {SnapName}: {Brief description of snap purpose and key configuration}
...

Data Flow:
{Source} -> {Parse/Transform steps} -> {Destination}

Error Handling:
{Description of error routing and handling strategy}

Configuration Parameters:
- {param_name}: {description and default value}
...

Execution Validation:
- Fully executable: {Yes/No}
- Test segment needed: {Yes/No}
"""

# Standard imports for SLPy
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.utils.open_view import OPEN_VIEW
from slpy.modules.Pipeline.utils import Expr
from slpy.modules.Pipeline.param_table.ParamTable import ParamTable
# Expression library import (if .expr file is generated)
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries

# Snap imports (import only snaps used in this pipeline)
from slpy.modules.Snap.BinaryFileReader import BinaryFileReader
from slpy.modules.Snap.TransformCSVParser import TransformCSVParser
from slpy.modules.Snap.TransformMapper import TransformMapper
from slpy.modules.Snap.TransformJSONFormatter import TransformJSONFormatter
from slpy.modules.Snap.BinaryFileWriter import BinaryFileWriter
from slpy.modules.Snap.FlowFilter import FlowFilter
from slpy.modules.Snap.FlowRouter import FlowRouter

# Pipeline initialization
p = Pipeline(label='{Descriptive Pipeline Name}')

# Pipeline parameters (if needed)
# All parameters are strings by default - cast in expressions if needed
p.param_table = ParamTable(param=[
    ParamTable.ParamItem(
        capture=True,  # Capture parameter value at runtime
        key='input_file_path',  # Parameter name (access as _input_file_path)
        value='/data/input.csv',  # Default value (always string)
        data_type='string'  # Data type (string, number, boolean)
    ),
    ParamTable.ParamItem(
        capture=True,
        key='batch_size',
        value='1000',  # Default as string
        data_type='number'
    ),
    ParamTable.ParamItem(
        capture=True,
        key='debug_mode',
        value='false',  # Boolean as string
        data_type='boolean'
    )
])

# Expression library configuration (REQUIRED when .expr file is generated)
# This imports the expression library so functions can be called via lib.{alias}.*
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='{name}_helpers.expr',  # Path to the generated .expr file
        as_='helpers'                 # Alias for use in expressions (lib.helpers.*)
    )
])

# Snap instantiation with detailed configuration
# Each snap should have clear label and purpose

# READ phase - Binary file input
snap_0 = BinaryFileReader(
    label="Read CSV File from S3",
    file_path=Expr("_input_file_path"),  # Use parameter (Expr required for _)
    # Additional configuration as needed
)

# PARSE phase - Convert binary to documents
snap_1 = TransformCSVParser(
    label="Parse CSV to Documents",
    has_header=True,
    delimiter=',',
    quote_character='"',
    # Additional configuration as needed
)

# TRANSFORM phase - Data transformations
snap_2 = TransformMapper(
    label="Transform Customer Data",
    mapping={
        # Map output fields from input document ($)
        'customer_id': Expr("$id"),  # Direct field copy
        'full_name': Expr("$first_name + ' ' + $last_name"),  # Concatenation
        'email': Expr("$email.toLowerCase()"),  # Method chaining
        'order_total': Expr("$order_amount * 1.08"),  # Arithmetic
        'is_vip': Expr("$order_count > 10"),  # Boolean expression
        'created_date': Expr("Date.now()"),  # Built-in function
        # Expression library reference (REQUIRED when .expr file generated)
        # Use lib.helpers.* to call functions from {name}_helpers.expr
        'discount': Expr("lib.helpers.calculate_discount($tier, $amount)"),
        'formatted_phone': Expr("lib.helpers.format_phone($phone)"),
        'category': Expr("lib.helpers.categorize_score($score)")
    }
)

# Optional: Filtering
snap_3 = FlowFilter(
    label="Filter Active Customers",
    filter_expression=Expr("$status == 'active' && $order_total > 0")  # Expr for $
)

# Optional: Routing
snap_4 = FlowRouter(
    label="Route by Region",
    routes=[
        FlowRouter.RoutesItem(
            condition=Expr("$region == 'US'"),
            label="US Region"
        ),
        FlowRouter.RoutesItem(
            condition=Expr("$region == 'EU'"),
            label="EU Region"
        )
    ]
)

# FORMAT phase - Convert documents to binary
snap_5 = TransformJSONFormatter(
    label="Format as JSON",
    pretty_print=True  # Human-readable JSON
)

# WRITE phase - Binary file output
snap_6 = BinaryFileWriter(
    label="Write JSON to S3",
    filename="/data/output.json"  # Plain string (no Expr needed)
)

# Connections - Define data flow between snaps
# Always specify type compatibility

# READ -> PARSE (binary -> binary)
p.connect(
    src=snap_0,
    dst=snap_1,
    src_view_id="output0",  # Output view of source snap
    dst_view_id="input0",   # Input view of destination snap
    src_output_type="binary",  # Source outputs binary
    dst_input_type="binary"    # Destination expects binary
)

# PARSE -> TRANSFORM (document -> document)
p.connect(
    src=snap_1,
    dst=snap_2,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",  # Parser outputs documents
    dst_input_type="document"    # Mapper expects documents
)

# TRANSFORM -> FILTER (document -> document)
p.connect(
    src=snap_2,
    dst=snap_3,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document"
)

# FILTER -> FORMAT (document -> document)
p.connect(
    src=snap_3,
    dst=snap_5,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document"
)

# FORMAT -> WRITE (binary -> binary)
p.connect(
    src=snap_5,
    dst=snap_6,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="binary",  # Formatter outputs binary
    dst_input_type="binary"    # Writer expects binary
)

# Error handling connections (if applicable)
# Connect error views to error pipeline or logging

# Example: Map error view to error handler
# p.connect(
#     src=snap_2,
#     dst=snap_error_handler,
#     src_view_id="error0",  # Error output view
#     dst_view_id="input0",
#     src_output_type="document",
#     dst_input_type="document"
# )
```

### Expression Library Template (.expr)

```javascript
{
    // Constants (simple values)
    tax_rate: 0.08,
    max_discount: 0.30,
    default_currency: 'USD',

    // Date/Time Helpers (single-expression functions)
    // Date.now().toString(format) uses Java-style patterns; quoted literals work (e.g., 'T' → T)
    get_today: () => Date.now().toString("yyyy-MM-dd"),
    get_today_iso: () => Date.now().toString("yyyy-MM-dd"),
    get_timestamp: () => Date.now().toString("yyyyMMdd'T'HHmmss"),
    prev_month_start: () => Date.now().minusMonths(1).withDayOfMonth(1),
    prev_month_end: () => Date.now().withDayOfMonth(1).minusDays(1),
    current_quarter_start: () => Date.now().minusMonths((Date.now().getMonth() - 1) % 3).withDayOfMonth(1),

    // Formatting Functions
    format_phone: (phone) => phone.replace(/[^0-9]/g, ''),
    format_currency: (amount) => '$' + amount.toFixed(2),
    format_full_name: (first, last) => (first + ' ' + last).trim().toUpperCase(),

    // Business Logic (ternary for conditionals)
    calculate_discount: (tier, amount) =>
        (tier == 'platinum' ? amount * 0.80 :
        (tier == 'gold' ? amount * 0.85 :
        (tier == 'silver' ? amount * 0.90 :
        (tier == 'bronze' ? amount * 0.95 :
        amount)))),

    calculate_shipping: (weight, zone) =>
        (zone == 'domestic' ?
            (weight < 5 ? 10 : (weight < 10 ? 15 : 20)) :
        (zone == 'international' ?
            (weight < 5 ? 25 : (weight < 10 ? 40 : 60)) :
        0)),

    // Categorization
    categorize_age: (age) =>
        (age < 18 ? 'minor' :
        (age < 65 ? 'adult' :
        'senior')),

    categorize_score: (score) =>
        (score >= 90 ? 'A' :
        (score >= 80 ? 'B' :
        (score >= 70 ? 'C' :
        (score >= 60 ? 'D' :
        'F')))),

    // Validation (return boolean)
    is_valid_email: (email) => email.contains('@') && email.contains('.'),
    is_valid_zip: (zip) => zip.match(/^\d{5}(-\d{4})?$/) != null,
    is_weekend: (date) => date.getDay() == 0 || date.getDay() == 6,

    // Array Operations (use .map, .filter, .reduce - no loops)
    sum_amounts: (items) => items.map(i => i.amount).reduce((a, b) => a + b, 0),
    filter_active: (users) => users.filter(u => u.status == 'active'),
    extract_ids: (records) => records.map(r => r.id),

    // String Operations
    truncate: (str, len) => str.length > len ? str.substring(0, len) + '...' : str,
    capitalize: (str) => str.charAt(0).toUpperCase() + str.slice(1).toLowerCase(),
    remove_spaces: (str) => str.replace(/\s+/g, ''),

    // Conditional Logic (nested ternary)
    get_priority: (amount, customer_tier) =>
        (customer_tier == 'platinum' ? 'high' :
        (customer_tier == 'gold' ? (amount > 1000 ? 'high' : 'medium') :
        (customer_tier == 'silver' ? 'medium' :
        (amount > 500 ? 'medium' : 'low')))),

    // NEVER use this.otherFunction() (returns null in slpy exec) — use lib.<name>.fn() or inline
    calculate_total_with_tax: (amount) => amount + (amount * 0.08),
    calculate_tax: (amount) => amount * 0.08,

    // Complex calculations (inline all dependencies)
    calculate_net_price: (gross, discount_tier) =>
        (discount_tier == 'gold' ? gross * 0.8 : (discount_tier == 'silver' ? gross * 0.9 : gross))
        + ((discount_tier == 'gold' ? gross * 0.8 : (discount_tier == 'silver' ? gross * 0.9 : gross)) * 0.08),

    // Data Transformation (use individual target_path mappings in TransformMapper, not object literals)
    format_full_name: (first, last) => first + ' ' + last,
    categorize_age: (age) => (age >= 65 ? 'senior' : (age >= 18 ? 'adult' : 'minor'))
}
```

**Using Expression Library in Pipeline:**

```python
# In pipeline docstring, document expression library usage
"""
Expression Library: customer_helpers.expr
Functions used:
- lib.calculate_discount(tier, amount): Apply tier-based discount
- lib.format_phone(phone): Normalize phone number format
- lib.is_valid_email(email): Validate email format
"""

# In TransformMapper, reference library functions with lib.
snap_2 = TransformMapper(
    label="Transform with Library Functions",
    mapping={
        'discounted_price': Expr("lib.calculate_discount($tier, $amount)"),
        'phone_normalized': Expr("lib.format_phone($phone)"),
        'email_valid': Expr("lib.is_valid_email($email)"),
        'full_name': Expr("lib.format_full_name($first, $last)")
    }
)
```

---

## 11. Expression Gotchas & Limitations

This section documents critical gotchas, edge cases, and platform-specific limitations that developers encounter when working with SnapLogic expressions. These 12 gotchas are the canonical list -- always check against them before delivering pipelines.

### Gotcha 1: Nested Ternary Parentheses Requirement

**CRITICAL:** When nesting ternary expressions (a ternary within another ternary's branches), you **must** wrap the nested ternary in parentheses or SnapLogic's parser will fail.

#### Single ternary - NO parentheses needed
```javascript
$status == 'A' ? 'Active' : 'Inactive'
```

#### Nested ternary - Parentheses REQUIRED
```javascript
// WRONG - Parser error! Missing parentheses around nested ternary
$status == 'A' ? 'Active' : $status == 'P' ? 'Pending' : 'Unknown'

// CORRECT - Nested ternary wrapped in parentheses
$status == 'A' ? 'Active' : ($status == 'P' ? 'Pending' : 'Unknown')
```

#### Multiple levels - Each nested level needs parentheses
```javascript
$score >= 90 ? 'A' : ($score >= 80 ? 'B' : ($score >= 70 ? 'C' : 'F'))
```

#### Long dispatch chain (5+ cases) — same pattern scales
```javascript
// WRONG — bare chain, parser rejects at second ?
$type == 'A' ? 1 : $type == 'B' ? 2 : $type == 'C' ? 3 : $type == 'D' ? 4 : $type == 'E' ? 5 : 0

// CORRECT — every else-branch parenthesized
$type == 'A' ? 1 : ($type == 'B' ? 2 : ($type == 'C' ? 3 : ($type == 'D' ? 4 : ($type == 'E' ? 5 : 0))))
```

#### .expr file format for long chains
```javascript
{
  map_type: (t) =>
    t == 'A' ? 1 :
    (t == 'B' ? 2 :
    (t == 'C' ? 3 :
    (t == 'D' ? 4 :
    (t == 'E' ? 5 :
    0))))
}
```

#### Rule of thumb
- **No nesting?** No parentheses needed: `condition ? a : b`
- **Nesting in false branch?** Parentheses required: `condition ? a : (condition2 ? b : c)`
- **N cases?** Every else-branch gets parentheses. N conditions = N-1 opening parens before the default.

#### Common mistakes to avoid
```javascript
// WRONG - Ambiguous parsing without parentheses
a ? b : c ? d : e

// CORRECT - Explicit grouping
a ? b : (c ? d : e)

// WRONG - Missing inner parentheses for triple nesting
a ? b : c ? d : e ? f : g

// CORRECT - All nested levels wrapped
a ? b : (c ? d : (e ? f : g))
```

**Why this matters:** The grammar uses `logical_or_expr` for ternary branches, which does not include the ternary rule itself. This means bare nested ternaries are naturally rejected. Wrapping in parentheses creates a grouped expression that re-enables the full expression grammar. Note: other operations (method calls like `.toFixed(2)`, arithmetic like `+ '-'`, and array access like `[idx]`) work freely inside ternary branches without extra parentheses.

### Gotcha 2: Nested Array Operation Limitations

**CRITICAL:** SnapLogic expressions have significant limitations when working with nested arrays. Many patterns that work in standard JavaScript do NOT work in SnapLogic.

#### What DOESN'T Work (Anti-Patterns)

| Pattern | Why It Fails | Example | Use Instead |
|---------|--------------|---------|-------------|
| `flatMap()` | Not supported in SnapLogic | `$array.flatMap(x => x.nested)` | `.reduce((acc, x) => acc.concat(x.nested), [])` |
| `.flat(depth)` | Not supported | `$array.flat()` | `.reduce((acc, x) => acc.concat(x), [])` |
| `.length` inside `.sum()` callback | Returns `null` | `$array.sum(x => x.nested.length)` | See reduce+concat pattern below |
| Nested `.sum()` calls | Inner `.sum()` fails | `$array.sum(x => x.nested.sum(y => 1))` | Flatten first, then sum |
| `.length` inside `.reduce()` callback | Returns `null` | `$array.reduce((sum, x) => sum + x.nested.length, 0)` | Flatten first, then `.length` |
| `.includes()` (string OR array) | Not supported | `$str.includes('x')` / `$arr.includes(x)` | `$str.contains('x')` / `$arr.indexOf(x) != -1` |
| `.at(index)` | Not supported | `$arr.at(-1)` | `$arr[$arr.length - 1]` |
| `Array.isArray(x)` | Not supported | `Array.isArray($value)` | `($value != null && $value.length != null)` |
| `.every(fn)` / `.some(fn)` | Not supported | `$arr.every(x => x > 0)` | `.filter(x => !(x > 0)).length == 0` / `.filter(x => x > 2).length > 0` |
| `.forEach(fn)` / `.entries()` / `.keys()` / `.values()` | Not supported (no iteration side effects in expressions) | `$arr.forEach(...)` | Use `.map()` / `.filter()` / `.reduce()` instead |
| `.fill()` | Not supported | `$arr.fill(0)` | Build new array with `.map()` |
| `.trimStart()` / `.trimEnd()` | Not supported — platform uses `left`/`right` aliases | `$str.trimStart()` | `$str.trimLeft()` / `$str.trimRight()` |
| `.padStart(n, c)` / `.padEnd(n, c)` | Not supported | `$s.padStart(3, '0')` | `('000' + $s).slice(-3)` |
| `Object.assign(target, ...src)` | Not supported | `Object.assign({}, $a, $b)` | `{}.extend($a, $b)` or spread `{...$a, ...$b}` |
| `Object.fromEntries(arr)` | Not supported | `Object.fromEntries([['a',1]])` | `{}.extend(arr)` |

#### What DOES Work (Correct Patterns)

| Use Case | Correct Pattern |
|----------|-----------------|
| **Count nested arrays** | `$parent.reduce((acc, p) => acc.concat(p.children \|\| []), []).length` |
| **Sum numeric fields** | `$array.sum(x => x.numericField)` |
| **Filter and count** | `$array.filter(x => x.condition == true).length` |
| **Safe array length** | `($array ? $array.length : 0)` |
| **Null check existence** | `$field != null ? 1 : 0` |
| **String prefix check** | `$str.startsWith('prefix')` |
| **Current timestamp** | `Date.now()` (returns ISO string) |

#### The reduce+concat Pattern (Key Pattern)

When counting elements across nested arrays, use `reduce()` with `concat()` to flatten first, then apply `.length`:

```javascript
// CORRECT: Flatten with reduce+concat, then .length
$cfd_data.billing_periods.reduce((acc, bp) => acc.concat(bp.settlement_units || []), []).length

// Returns: 3 (if there are 3 total settlement_units across all billing_periods)
```

**Why this works:**
1. `reduce()` iterates over each parent element
2. `concat()` appends child arrays to an accumulator array
3. `|| []` provides null safety for missing nested arrays
4. `.length` is called on the final flattened array (outside any callback)

#### Multi-Level Nesting Examples

**1-Level Nesting (parent -> children):**
```javascript
// Count all items across all orders
$orders.reduce((acc, order) => acc.concat(order.items || []), []).length

// Sum quantities across all order items
$orders.reduce((acc, order) => acc.concat(order.items || []), []).sum(item => item.quantity)
```

**2-Level Nesting (grandparent -> parent -> children):**
```javascript
// First flatten to parents, then flatten to children
$billing_periods
  .reduce((acc, bp) => acc.concat(bp.settlement_units || []), [])
  .reduce((acc, su) => acc.concat(su.line_items || []), [])
  .length
```

#### Common Mistakes vs Correct Patterns
```javascript
// WRONG - flatMap not supported
$orders.flatMap(o => o.items).length

// CORRECT - reduce+concat pattern
$orders.reduce((acc, o) => acc.concat(o.items || []), []).length

// WRONG - .length in sum callback returns null
$orders.sum(o => o.items.length)

// CORRECT - flatten first, then count
$orders.reduce((acc, o) => acc.concat(o.items || []), []).length

// WRONG - .length in reduce callback returns null
$orders.reduce((sum, o) => sum + o.items.length, 0)

// CORRECT - flatten with concat, then .length outside
$orders.reduce((acc, o) => acc.concat(o.items || []), []).length
```

### Gotcha 3: Pipeline Parameter String Casting

Pipeline parameters arrive as **strings** by default. This causes unexpected behavior with arithmetic and comparisons.

```javascript
// Pipeline parameters arrive as STRINGS
// WRONG - concatenates strings
_limit + 10  // "5010" not 60

// CORRECT - cast first
parseInt(_limit) + 10  // 60

// For float values
parseFloat(_threshold) * 1.5
```

### Gotcha 4: Date Formatting with .toString(format)

`Date.now().toString(format)` with Java-style format patterns works in both `slpy exec` and platform. Single-quoted literals in format strings produce literal output (e.g., `'T'` → `T`):

```javascript
Date.now().toString("yyyy-MM-dd")                   // "2026-01-15"
Date.now().toString("yyyyMMdd'T'HHmmss")            // "20260115T143522"
Date.now().toString("yyyy-MM-dd'T'HH:mm:ss")        // "2026-01-15T14:35:22"
```

`Date.parse(dateStr, format)` supports Java-style format patterns. UTC suffix normalization is handled automatically.

**Note:** `Crypto.uuid()` still returns null in `slpy exec` -- it is platform-only. Mark as SKIPPED in test assertions.

### Gotcha 5: Strict Equality Not Supported

SnapLogic expressions do NOT support strict equality operators.

```javascript
// WRONG - Not supported
$status === 'active'
$value !== null

// CORRECT - Use loose equality
$status == 'active'
$value != null
```

**Also:** `.length` is a property, not a method. Use `$arr.length`, never `$arr.length()`.

### Gotcha 6: Expression Library Function Restrictions

Expression libraries only support single-expression arrow functions. Multi-statement functions with braces, `return`, `if/else`, loops, and variable declarations are NOT supported. See Section 9 for the complete expression library format specification and validation checklist.

```javascript
// WRONG - Multi-line with braces
calculate: (x) => {
  const result = x * 2;
  return result;
}

// CORRECT - Single expression
calculate: (x) => x * 2

// WRONG - if/else statement
check: (x) => {
  if (x > 0) return 'positive';
  else return 'non-positive';
}

// CORRECT - Ternary expression
check: (x) => x > 0 ? 'positive' : 'non-positive'
```

### Gotcha 7: Null in Boolean Chains

SnapLogic follows standard JavaScript short-circuit evaluation:

```javascript
null != null       // -> false (safe as null guard)
null || true       // -> true (standard short-circuit)
null && true       // -> null (returns falsy left operand)
```

**Behavior depends on `null_safe_access`:**

With `null_safe_access=True`, absent fields resolve to `null` per-subexpression, so guard patterns and OR/AND chains work correctly:
```javascript
// null_safe_access=True — absent fields become null, short-circuit works as expected
$absent != null                     // -> false
$absent != null || $present != null // -> true (each side evaluates independently)
$absent != null ? $absent : 'default' // -> 'default'
```

With `null_safe_access=False` (the default), accessing an absent field throws an error. Use ternary guards or ensure upstream data includes all referenced fields:
```javascript
// null_safe_access=False (default) — $absent throws, so guard with hasPath or ternary
hasPath($, "absent") ? $absent : null
```

> **Edge case:** Raw `null && X` returns `null` (not `false`). If both sides of an `||` produce `null`, the chain returns `null`: `(null && X) || (null && Y) → null`. This only happens when passing literal null to `&&`, not when using `!= null` guards.

### Gotcha 8: Expression Library Comment Parsing Bug

Comments in `.expr` files are NOT ignored by the parser. Both `/* */` block comments and `//` line comments are tokenized as expressions, causing parse errors.

```javascript
// WRONG - Comments cause Unexpected token errors
{
  /* Helper function for formatting */
  format: (x) => x + '',

  // Converts to uppercase
  upper: (x) => x.toUpperCase()
}

// CORRECT - No comments at all in .expr files
{
  format: (x) => x + '',
  upper: (x) => x.toUpperCase()
}
```

### Gotcha 9: this. Cross-References Return Null in slpy exec

Expression library functions are evaluated **independently** in `slpy exec`. Calling another function in the same library via `this.otherFunction()` will pass validation but silently return null at runtime.

```javascript
// WRONG - this.helper() returns null in slpy exec
{
  helper: (x) => x.trim().toLowerCase(),
  process: (x) => this.helper(x) + '_processed'  // -> null + '_processed' -> 'null_processed'
}

// CORRECT — Use lib.* cross-references (works in both slpy exec and platform)
{
  helper: (x) => x.trim().toLowerCase(),
  process: (x) => lib.utils.helper(x) + '_processed'
}

// ALSO CORRECT — Inline the logic
{
  helper: (x) => x.trim().toLowerCase(),
  process: (x) => x.trim().toLowerCase() + '_processed'
}
```

### Gotcha 10: Object Literals in Expr() Return Null

Using an object literal `{...}` as the root expression in `Expr()` returns null. This affects TransformMapper mappings that try to build objects inline.

```python
# WRONG - Object literal in Expr() returns null
TransformMapper(
    mapping=[
        MappingTableItem(
            expression=Expr("{'name': $first + ' ' + $last, 'age': $age}"),
            target_path='person'
        )
    ]
)

# CORRECT - Use individual target_path mappings with dotted paths
TransformMapper(
    mapping=[
        MappingTableItem(expression=Expr("$first + ' ' + $last"), target_path='person.name'),
        MappingTableItem(expression=Expr("$age"), target_path='person.age')
    ]
)
```

### Gotcha 11: Dictionary/Variable Access Inside Callbacks Returns Null

Document-level variables (`$dict`, `$lookup`) referenced inside `.filter()` or `.map()` callbacks silently return null. The callback scope cannot access outer document fields.

```javascript
// WRONG - $lookup[$key] inside .map() callback -> null
$items.map(item => $lookup[item.category])

// WRONG - $rates dictionary access inside .filter() -> null
$transactions.filter(t => $rates[t.currency] > 1.0)

// CORRECT - Use nested .filter() for cross-array lookups
$items.map(item => $categories.filter(c => c.id == item.category)[0].name)

// CORRECT - Nested .filter() for existence check
$transactions.filter(t => $rates.filter(r => r.currency == t.currency && r.value > 1.0).length > 0)
```

### Gotcha 12: TransformMapper Self-Referencing Fails

Expressions within a single TransformMapper snap cannot reference fields computed by other mappings in the same snap. Each mapping only sees the original input document.

```python
# WRONG - total_with_tax cannot see computed_subtotal (returns null)
TransformMapper(
    mapping=[
        MappingTableItem(expression=Expr("$price * $quantity"), target_path='computed_subtotal'),
        MappingTableItem(expression=Expr("$computed_subtotal * 1.1"), target_path='total_with_tax')  # null!
    ]
)

# CORRECT - Split into sequential mappers
snap_subtotal = TransformMapper(
    label='Compute Subtotal',
    pass_through=True,
    mapping=[
        MappingTableItem(expression=Expr("$price * $quantity"), target_path='computed_subtotal')
    ]
)
snap_total = TransformMapper(
    label='Compute Total',
    pass_through=True,
    mapping=[
        MappingTableItem(expression=Expr("$computed_subtotal * 1.1"), target_path='total_with_tax')
    ]
)
p.connect(src=snap_subtotal, dst=snap_total)

# 3-MAPPER PATTERN for test assertions: compute → check → status
snap_compute = TransformMapper(
    label='Compute Values',
    pass_through=True,
    mapping=[
        MappingTableItem(expression=Expr("$price * $quantity"), target_path='computed_total'),
    ]
)
snap_check = TransformMapper(
    label='Check Values',
    pass_through=True,
    mapping=[
        MappingTableItem(expression=Expr("$computed_total == $expected_total"), target_path='check_total'),
        MappingTableItem(expression=Expr("$computed_total > 0"), target_path='check_positive'),
    ]
)
snap_status = TransformMapper(
    label='Derive Status',
    pass_through=True,
    mapping=[
        MappingTableItem(expression=Expr("$check_total && $check_positive"), target_path='all_passed'),
    ]
)
p.connect(src=snap_compute, dst=snap_check)
p.connect(src=snap_check, dst=snap_status)
```

---

## 12. Anti-Patterns & Common Mistakes

Learn from these common errors with correct alternatives.

> **Note:** See Section 11 (Expression Gotchas) for additional anti-patterns related to expression language limitations, including: multi-line expression library functions, flatMap usage, .length in callbacks, this.otherFunction() cross-references, object literals in Expr(), TransformMapper self-referencing, and dictionary access inside callbacks.

### Mistake 0: Self-Referencing in Test Assertion Mappers

**WRONG — summary references check fields computed in the same mapper (returns null):**
```python
TransformMapper(mapping=[
    MappingTableItem(expression=Expr("$actual_name == $expected_name"), target_path='check_name'),
    MappingTableItem(expression=Expr("$actual_total == $expected_total"), target_path='check_total'),
    MappingTableItem(expression=Expr("$check_name && $check_total"), target_path='all_passed')  # null!
])
```

**CORRECT — split into compute → derive stages:**
```python
snap_checks = TransformMapper(label='Compute Checks', pass_through=True, mapping=[
    MappingTableItem(expression=Expr("$actual_name == $expected_name"), target_path='check_name'),
    MappingTableItem(expression=Expr("$actual_total == $expected_total"), target_path='check_total'),
])
snap_summary = TransformMapper(label='Derive Summary', pass_through=True, mapping=[
    MappingTableItem(expression=Expr("$check_name && $check_total"), target_path='all_passed'),
])
p.connect(src=snap_checks, dst=snap_summary)
```

See Gotcha 12 for details. **Rule:** Before generating any mapper, check if any `$field` in an expression matches a `target_path` in the same mapping table AND the field is not already present in the input document.

### Mistake 1: Missing Expr() Wrapper

**WRONG:**
```python
snap_0 = FlowFilter(
    filter_expression="$amount > 1000"  # Contains $ but no Expr()
)

snap_1 = BinaryFileReader(
    file_path=_input_path  # Uses _ parameter without Expr()
)

snap_2 = TransformMapper(
    mapping={
        'timestamp': "Date.now()"  # Function call without Expr()
    }
)
```

**CORRECT:**
```python
snap_0 = FlowFilter(
    filter_expression=Expr("$amount > 1000")  # Expr required for $
)

snap_1 = BinaryFileReader(
    file_path=Expr("_input_path")  # Expr required for _
)

snap_2 = TransformMapper(
    mapping={
        'timestamp': Expr("Date.now()")  # Expr required for function
    }
)
```

### Mistake 2: Type Mismatch Without Formatter/Parser

**WRONG:**
```python
# Mapper outputs document, writer expects binary
snap_0 = TransformMapper(...)
snap_1 = BinaryFileWriter(...)
p.connect(src=snap_0, dst=snap_1)  # ERROR: document -> binary mismatch
```

**CORRECT:**
```python
# Add formatter to convert document -> binary
snap_0 = TransformMapper(...)
snap_formatter = TransformJSONFormatter()  # Converts document to binary
snap_1 = BinaryFileWriter(...)

p.connect(src=snap_0, dst=snap_formatter)  # document -> document
p.connect(src=snap_formatter, dst=snap_1)  # binary -> binary
```

**WRONG:**
```python
# File reader outputs binary, mapper expects document
snap_0 = BinaryFileReader(...)
snap_1 = TransformMapper(...)
p.connect(src=snap_0, dst=snap_1)  # ERROR: binary -> document mismatch
```

**CORRECT:**
```python
# Add parser to convert binary -> document
snap_0 = BinaryFileReader(...)
snap_parser = TransformCSVParser()  # Converts binary to document
snap_1 = TransformMapper(...)

p.connect(src=snap_0, dst=snap_parser)  # binary -> binary
p.connect(src=snap_parser, dst=snap_1)  # document -> document
```

### Mistake 3: Using REST Snaps Instead of APISuiteHTTPClient

**WRONG:**
```python
from slpy.modules.Snap.RestGet import RestGet

snap_0 = RestGet(
    url='https://api.example.com/data'
)
```

**CORRECT:**
```python
from slpy.modules.Snap.APISuiteHTTPClient import APISuiteHTTPClient

snap_0 = APISuiteHTTPClient(
    label="GET Request",
    method='GET',
    url='https://api.example.com/data'
)
```

### Mistake 4: Over-tooling (Too Many Pygen Calls)

**WRONG:**
```
# 10+ tool calls - excessive
1. pygen_query_pipeline_examples("csv to database")
2. pygen_query_snap_examples("csv parser")
3. pygen_query_snap_examples("database writer")
4. pygen_validate_snap_names([...])
5. pygen_get_snap_documentation([snap1])
6. pygen_get_snap_documentation([snap2])
7. pygen_get_snap_documentation([snap3])
8. pygen_get_snap_parameters([snap1])
9. pygen_get_snap_parameters([snap2])
10. pygen_query_pipeline_examples("csv to database") again
```

**CORRECT:**
```
# 3-4 tool calls - efficient
1. pygen_query_pipeline_examples("csv to database")
2. pygen_validate_snap_names([...], do_get_parameters=true)
3. pygen_get_snap_documentation([connectivity_snaps_only])
4. Generate with available information
```

### Mistake 5: Python Concatenation Instead of SnapLogic Expression

**WRONG:**
```python
snap_0 = BinaryFileReader(
    file_path="/data/" + _environment + "/file.csv"  # Python concatenation
)
```

**CORRECT:**
```python
snap_0 = BinaryFileReader(
    file_path=Expr("'/data/' + _environment + '/file.csv'")  # SnapLogic expression
)
```

### Mistake 6: Unnecessary Reader Input Connection

**WRONG:**
```python
snap_0 = BinaryFileReader(...)
# Unnecessary OPEN_VIEW connection (anti-pattern)
p.connect(src=OPEN_VIEW.INPUT, dst=snap_0, src_view_id="INPUT", dst_view_id="input0")
```

**CORRECT:**
```python
snap_0 = BinaryFileReader(...)
snap_1 = TransformCSVParser(...)
# Reader starts pipeline - no input connection needed
p.connect(src=snap_0, dst=snap_1)  # Only output connection
```

### Mistake 7: Multiple Mappings to Same Target Path

```python
# WRONG — second mapping silently overwrites first (last write wins)
mapping_table=[
    MappingTableItem(expression=Expr("$type == 'gas' ? $gas_value : null"), target_path='$.result'),
    MappingTableItem(expression=Expr("$type == 'elec' ? $elec_value : null"), target_path='$.result'),
]

# CORRECT — single mapping with consolidated ternary
mapping_table=[
    MappingTableItem(expression=Expr("$type == 'gas' ? $gas_value : ($type == 'elec' ? $elec_value : null)"), target_path='$.result'),
]
```

### Mistake 8: Invalid Enum Values

**`file_action`:** `'CREATE'` does not exist. Valid values: `'OVERWRITE'` (default), `'APPEND'`, `'IGNORE'`, `'ERROR'`. Omit unless the pipeline specifically needs `'APPEND'`, `'IGNORE'`, or `'ERROR'` — defaults to `'OVERWRITE'`.

**`entity_type`** (APISuiteHTTPClient): `'text'`, `'json'`, `'form'`, `'string'` do NOT exist. Valid values: `'none'` (default), `'multipart'`, `'x-www-form-urlencoded'`, `'raw'`, `'binary'`. Omit unless the pipeline specifically needs `'binary'`, `'multipart'`, or `'x-www-form-urlencoded'` — defaults to `'none'` (correct for raw body via `raw_entity`).

### Mistake 9: Plain Values Instead of Item Classes

```python
# WRONG — plain strings (silent corruption, no error)
user_defined_header=['Name', 'Age', 'Email']

# CORRECT — Item class objects
user_defined_header=[
    TransformCSVFormatter.UserDefinedHeaderItem(header_column='Name'),
    TransformCSVFormatter.UserDefinedHeaderItem(header_column='Age'),
    TransformCSVFormatter.UserDefinedHeaderItem(header_column='Email'),
]
```

Rule: If the snap parameter is `List[SomeItem]`, always construct `SomeItem(...)` objects. Never pass plain strings or dicts.

### Mistake 10: Expression for Child Pipeline Name

**WRONG:**
```python
snap_0 = FlowPipelineExecute(
    pipeline=Expr("_child_pipeline_name"),  # Expression prevents inlining
    params=[...]
)
```

**CORRECT:**
```python
snap_0 = FlowPipelineExecute(
    pipeline="ST001_INSPECTIONS",  # Literal name enables inlining
    params=[
        FlowPipelineExecute.ParamsItem(
            param_name="FileName",
            param_value=Expr("_DeltaFileName")  # Expr OK for param VALUES
        )
    ]
)
```

### Mistake 11: Unnecessary Expr() for Plain Values

**WRONG:**
```python
snap_0 = BinaryFileWriter(
    filename=Expr("'output.json'"),  # Unnecessary Expr() for plain string
    batch_size=Expr("1000")  # Unnecessary Expr() for number
)
```

**CORRECT:**
```python
snap_0 = BinaryFileWriter(
    filename='output.json',  # Plain string - no Expr()
    batch_size=1000  # Plain number - no Expr()
)
```

### Mistake 12: Skipping slpy translate Validation

**WRONG:** Generate SLPy code → deliver without running `slpy translate`.

**CORRECT:**
```
1. Generate SLPy code
2. slpy translate -src pipeline.py -dest pipeline.slp -strict
3. Fix any errors → re-translate until success
4. Deliver validated .py + generated .slp file
```

`slpy translate` is MANDATORY — it validates syntax AND generates `.slp` files (native SnapLogic JSON format, uploadable directly to platform). No MCP tool replaces it.

### Mistake 13: Not Validating Expression Libraries Before Delivery

**WRONG:**
```
1. Generate .expr file
2. Deliver to user without validation
3. User discovers syntax errors when pipeline fails
```

**CORRECT:**
```
1. Generate .expr file
2. Run: slpy validate-expression -expr-lib {file}.expr
3. Fix any errors
4. Re-validate until success
5. Deliver validated .expr file
```

**Why this matters:**
- Expression libraries have strict syntax restrictions (Rule 7)
- Validation catches errors before pipeline execution
- Provides immediate feedback for fixing issues

### Mistake 14: Generating Expression Library Without Using It

**WRONG:**
```python
"""
Pipeline Name: Payment Processor

Expression Library: payment_helpers.expr
Functions used:
- lib.helpers.generate_message_id(timestamp): Create unique message identifier
- lib.helpers.normalize_currency(code): Normalize currency code to uppercase
"""

# Expression library generated (payment_helpers.expr) but never imported or used!
# Pipeline docstring says: "lib.helpers.generate_message_id(timestamp)"
# But the actual code duplicates the logic inline:

from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.utils import Expr
# MISSING: ExpressionLibraries import

p = Pipeline(label='Payment Processor')
# MISSING: p.expression_libraries = ExpressionLibraries(...)

snap_0 = TransformMapper(
    mapping={
        # DUPLICATES library logic inline instead of calling lib.helpers.*
        'msg_id': Expr("'MSG-' + $timestamp.toString('yyyyMMddHHmmss') + '-' + Math.random().toString(16).substring(2, 10).toUpperCase()"),
        '@Ccy': Expr("record.currency == null ? 'GBP' : (record.currency.toUpperCase() == 'GBP' ? 'GBP' : ...)")
    }
)
```

**CORRECT:**
```python
"""
Pipeline Name: Payment Processor

Expression Library: payment_helpers.expr
Functions used:
- lib.helpers.generate_message_id(timestamp): Create unique message identifier
- lib.helpers.normalize_currency(code): Normalize currency code to uppercase
"""

from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.utils import Expr
# Import the expression library module
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries

p = Pipeline(label='Payment Processor')

# Configure expression library AFTER Pipeline initialization
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='payment_helpers.expr',
        as_='helpers'
    )
])

snap_0 = TransformMapper(
    mapping={
        # Use library functions instead of duplicating logic
        'msg_id': Expr("lib.helpers.generate_message_id($timestamp)"),
        '@Ccy': Expr("lib.helpers.normalize_currency(record.currency)")
    }
)
```

**Why this matters:**
- Expression libraries exist to centralize and reuse complex logic
- Duplicating logic inline defeats the purpose of the library
- Makes maintenance harder (changes needed in multiple places)
- Test pipelines verify library functions -- production must use the same functions
- Docstring becomes misleading if it documents functions that aren't actually used

### Mistake 15: Modifying Production Pipeline for Testing

**WRONG:**
```python
# Editing the production pipeline to replace API calls with file readers for testing
# countries_analysis.py (production file modified!)
snap_0 = BinaryFileReader(  # Was APISuiteHTTPClient - changed for testing
    label="Read Countries Data",
    file_path='countries_data.jsonl'
)
# Now production pipeline is broken and needs to be reverted
```

**CORRECT:**
```python
# Create a SEPARATE test segment file: countries_analysis_test.py
# Production pipeline (countries_analysis.py) is UNTOUCHED
# Test segment replaces non-executable snaps with file I/O but keeps all transforms identical

"""
Pipeline Name: Countries by Continent Analysis (Test Segment)

Test Segment for: countries_analysis.py
Non-executable snaps replaced:
- snap_0: APISuiteHTTPClient -> BinaryFileReader + TransformJSONParser (reads from countries_data.jsonl)

All transformation snaps are IDENTICAL to production pipeline.
"""

# snap_0 replacement: File reader instead of API call
snap_0 = BinaryFileReader(
    label="Read Test Data (replaces API call)",
    file_path='countries_data.jsonl'
)
snap_1 = TransformJSONParser(
    label="Parse Test JSONL",
    json_lines=True
)
# ... all remaining transformation snaps IDENTICAL to production ...
```

**Why this matters:**
- Production pipelines must remain deployment-ready at all times
- Test segment files (`{name}_test.py`) isolate testing changes from production code
- Transformation snaps MUST be identical between production and test segment to ensure valid testing
- Test segment files should be clearly documented as test variants in their docstring

### Mistake 16: Quoting extract_entity_path as a String Literal

**WRONG:**
```python
# Inner quotes create a string literal -- platform treats '$.entity' as literal text, not a path
extract_entity_path=Expr("'$.entity'")
```

**CORRECT:**
```python
# Bare $.entity is a document field reference that evaluates to the entity value at runtime
extract_entity_path=Expr("$.entity")
```

**Why this matters:**
- `$.entity` with the `$` prefix IS a document field reference (Rule 1 applies), so `Expr()` is required
- However, the inner quotes `'...'` must NOT be added -- they turn `$.entity` into a string literal instead of a path expression
- On the SnapLogic platform, this causes entity extraction to silently fail: the snap receives the literal string `$.entity` instead of navigating to the `entity` field in the response document
- `slpy exec` will raise a `ValueError` if it detects quoted JSONPath in `extract_entity_path`, but the platform fails silently -- making this a particularly dangerous bug to ship

### Mistake 17: Referencing TransformGroupByFields Keys at Root Level

**WRONG:**
```python
# Group-by field referenced at document root -- resolves to null on the platform
snap_map = TransformMapper(
    label="Summarize by Continent",
    mapping={
        "continent": Expr("$continent"),  # null on platform
        "count": Expr("$countries.length")
    }
)
```

**CORRECT:**
```python
# Group-by field referenced under $groupBy -- works on the platform
snap_map = TransformMapper(
    label="Summarize by Continent",
    mapping={
        "continent": Expr("$groupBy.continent"),  # Correct path
        "count": Expr("$countries.length")
    }
)
```

**Why this matters:**
- Both the SnapLogic platform and `slpy exec` wrap group-by field values under a `groupBy` key in the output document (see Rule 8)
- `$continent` resolves to `null` because the value lives at `$groupBy.continent` -- `slpy exec` will correctly surface this error during local testing
- Always use `$groupBy.<field>` for group-by key references in downstream snaps

### Mistake 18: Using TransformUnion (Does Not Exist)

**WRONG:**
```python
from slpy.modules.Snap.TransformUnion import TransformUnion
snap_merge = TransformUnion(label='Merge Branches')  # ERROR: snap not in catalog
```

**CORRECT:**
```python
from slpy.modules.Snap.FlowUnion import FlowUnion
snap_merge = FlowUnion(label='Merge Branches', preserve_order='Unsorted')
```

### Mistake 19: FlowRouter with default_view_name

**WRONG:**
```python
snap_router = FlowRouter(
    label='Route by Type',
    first_match=True,
    default_view_name='other',  # Invalid parameter
    routes=[
        FlowRouter.RoutesItem(expression=Expr("$type == 'A'"), output_view_name='type_a')
    ]
)
```

**CORRECT:**
```python
# Use explicit catch-all route instead of default_view_name
snap_router = FlowRouter(
    label='Route by Type',
    first_match=True,
    routes=[
        FlowRouter.RoutesItem(expression=Expr("$type == 'A'"), output_view_name='type_a'),
        FlowRouter.RoutesItem(expression=Expr("$type != 'A'"), output_view_name='other')
    ]
)
```

---

## 13. Troubleshooting

### Common Validation Errors and Solutions

#### Debugging Workflow for Expression Library Validation Errors

When `slpy translate` fails with expression syntax errors:

1. **Locate the error line** - Check the line number in the error message
2. **Look for syntax violations** at or near the reported line
3. **Verify forbidden syntax:**
   - Braces `{ }` after arrow functions
   - `return` statements
   - `===` or `!==` (use `==` and `!=` instead)
   - Variable declarations (`var`, `let`, `const`)
   - `if/else` statements or loops
4. **Check nested ternaries** - Are they properly wrapped in parentheses?
5. **Re-run validation:** `slpy translate -src file.py -dest file.slp -strict`

#### Prevention Checklist for Expression Libraries

See the **Restrictions** section in §10 for the complete forbidden constructs list. Key items: single-expression arrows only, `==`/`!=` not `===`/`!==`, no `this.` cross-refs, no comments in `.expr`, nested ternaries wrapped in parens, no `String()`/`Number()`/`Boolean()` constructors, no IIFE.

#### Expr() Type Errors

**Error**: Type mismatch in comparison - expected number, got string
**Fix**: Use `Expr('1.5')` not `Expr("'1.5'")` for numeric values. Quoting inside Expr() creates a string literal.

### Debugging Workflow for Expression Errors

When expressions produce unexpected results (especially null values):

1. **Check against Section 11 gotchas** - Most expression errors match one of the 12 documented gotchas
2. **Create a minimal debug pipeline** - Isolate the suspect expression in a 4-5 snap pipeline with hardcoded test data. Create the debug pipeline in the working directory alongside `.expr` files, not in `/tmp/` — `.expr` paths are resolved relative to the pipeline file (see Prerequisites line 5 above)
3. **Run with `slpy exec`** - Execute the debug pipeline to see actual output values
4. **Check null patterns** - Compare output against the Silent Failures table below
5. **Verify Expr() usage** - Ensure expressions with `$`, `_`, or function calls are wrapped in `Expr()`
6. **Test expression library functions independently** - Use `slpy validate-expression -expr-lib {file}.expr` to catch syntax issues before pipeline execution

### Execution Validation Errors (`slpy execute`)

**Error**: Unsupported snap type '{SnapName}'
**Cause**: The pipeline contains a snap that `slpy execute` cannot run locally (e.g., Salesforce, Snowflake, SAP snaps).
**Fix**: Create a test segment pipeline replacing unsupported snaps with file I/O. Run `slpy exec --list-snaps` to check supported snaps.

**Error**: File not found: '{file_path}'
**Cause**: Input data file does not exist at the specified path.
**Fix**: Create the test data file (JSONL format recommended, 5-20 records matching expected schema) or update the file path.

**Error**: Null reference at snap '{snap_label}': Cannot read property '{field}' of null
**Cause**: Test data is missing expected fields, or upstream snap produced null output.
**Fix**: Verify test data matches the expected input schema. Add `null_safe_access=True` if the pipeline genuinely expects missing fields — with this flag, absent fields resolve to `null` and boolean guard chains (e.g., `$field != null && ...`) work correctly.

**Error**: Pipeline parameter '{param}' not defined
**Cause**: Pipeline uses parameters but they were not passed via `-e` flag.
**Fix**: Pass parameters using `-e` flag: `slpy exec pipeline.py -e param_name=value`. Note: parameter names do NOT use underscore prefix in the `-e` flag (use `batch_size=100`, not `_batch_size=100`).

**Error**: Connection type mismatch during execution
**Cause**: Runtime type incompatibility between snaps (same as translate error, but caught during data flow).
**Fix**: Add appropriate formatter/parser between snaps (see Rule 2).

### Pipeline Parameter `-e` Flag Syntax

When passing pipeline parameters to `slpy execute`, use the `-e` flag:

```bash
# Correct: parameter name without underscore prefix
slpy exec pipeline.py -e input_path=/data/test.jsonl -e batch_size=100

# Wrong: do NOT use underscore prefix with -e flag
slpy exec pipeline.py -e _input_path=/data/test.jsonl  # ERROR
```

Inside the pipeline, parameters are accessed with underscore prefix (`_input_path`), but the `-e` flag uses the parameter key name without the prefix.

### Silent Failures in `slpy exec` (No Error Message -- Output is Null)

These produce NO error -- you must detect null values in output and reason about causes. They account for the majority of debugging time.

| Pattern | Symptom | Fix |
|---------|---------|-----|
| `$dict[$key]` inside `.filter()`/`.map()` callback | Field returns null | Use nested `.filter()` for lookups (see Section 11, Gotcha 11) |
| `this.functionName()` in expression library | Function returns null | Use `lib.<name>.fn()` or inline (see Section 11, Gotcha 9) |
| Object literal `{...}` in `Expr()` | Mapping returns null | Use individual `target_path` entries (see Section 11, Gotcha 10) |
| `.filter((v,k) => ...)` on objects | Works correctly | Returns filtered object (fixed) |
| `String()` / `Number()` / `Boolean()` constructors | Return null | Use `'' + expr`, `parseFloat(x)`, `x == 'true'` |
| `null != null` | Returns `false` (standard JS) | Safe to use as null guard — `$field != null && ...` works correctly |
| `null \|\| true` | Returns null (not true) | Ensure non-null operands |
| TransformMapper self-reference | Computed field returns null | Split into sequential mappers (see Section 11, Gotcha 12) |
| `Crypto.uuid()` | Returns null | Platform-only -- mark as SKIPPED in tests |

**Debugging approach:** When `slpy exec` produces null where a value is expected, create a minimal debug pipeline (4-5 snaps) isolating the suspect expression. Check against the patterns above before investigating further.

### Comparison: `slpy translate` vs `slpy execute`

| Aspect | `slpy translate` | `slpy execute` |
|--------|------------------|----------------|
| **Purpose** | Syntax validation + .slp generation | Runtime validation of data flow |
| **What it catches** | Invalid snap names, type mismatches, missing Expr(), syntax errors, expression library issues | Null references, incorrect transformations, wrong output structure, logic errors, data type issues |
| **When to run** | ALWAYS (mandatory) | When feasible (recommended) |
| **Prerequisites** | Valid .py file | Successful translate + supported snaps + input data |
| **Output** | .slp file (deployment artifact) | Pipeline output files + execution log |
| **Snap support** | All snaps | Subset only (run `slpy exec --list-snaps`) |
| **Speed** | Fast (static analysis) | Slower (actual data processing) |
| **Replaces the other?** | No -- both are complementary | No -- translate is always required first |
