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

**When to use:** ALWAYS before generation (mandatory Checkpoint 1), with `do_get_parameters=true`

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
- `warnings`: Isolated snaps (declared but not connected), plus open views slpy assigned so a snap meets its minimum view count. The latter are informational: an assigned **output** view is fine unless a destination was intended; an assigned **input** view means a leg is unwired — connect it or confirm the input is meant to be open. Tell the user either way.

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
- `pack` (optional): Snap pack name, e.g., "Snowflake", "Salesforce", "Binary", "Transform". Exact-match — note S3-related snaps span two packs: `pack="S3"` (S3Select, S3Upload, …) and `pack="Binary"` (`BinaryS3File*`).

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
cd {pipeline_dir} && slpy translate -src {pipeline_name}.py -dest {pipeline_name}.slp -strict -expr
```

**What it does:**
- Validates SLPy syntax (snap names, connections, expressions, parameters)
- Translates .py to .slp (native SnapLogic JSON pipeline format)
- Outputs deployment-ready pipeline files for platform upload
- Reports errors with line numbers for debugging

**CRITICAL:** This is the mandatory tool for final pipeline validation and .slp generation.

#### slpy exec (via Bash tool)

**Purpose:** Execute SLPy pipelines locally for runtime validation of data flow and transformation logic

**When to use:** RECOMMENDED after successful `slpy translate` (Checkpoint 7), when the pipeline uses execution-supported snaps

**IMPORTANT:** `slpy exec` is NOT a replacement for `slpy translate`. Both serve different purposes:
- `slpy translate` = syntax validation + .slp generation (MANDATORY)
- `slpy exec` = runtime validation of data flow (RECOMMENDED when feasible)
