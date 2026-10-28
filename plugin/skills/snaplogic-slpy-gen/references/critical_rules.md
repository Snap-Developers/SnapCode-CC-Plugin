## 5. Critical Generation Rules

These rules prevent 90% of SLPy generation errors. Study these carefully before generating any pipeline.

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
   - `_environment + '.csv'`
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
   - `'files/'`

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
    file_path=Expr("_environment + '/file.csv'")  # _ requires Expr()
)

# Function call - needs Expr()
snap_2 = TransformMapper(
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("Date.now()"), target_path="$.timestamp"),  # Function requires Expr()
        ]
    ),
)

# Plain string literal - no Expr()
snap_3 = BinaryFileWriter(
    filename='output.json'  # No $ or _ or functions - plain string
)

# Numeric literal - no Expr()
snap_4 = TransformCSVParser(
    skip_lines=2  # Plain number - no Expr()
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
    file_path=_environment + "/file.csv"  # ERROR: Python concat invalid
)

# WRONG - Unnecessary Expr() for plain string
snap_2 = BinaryFileWriter(
    filename=Expr("'output.json'")  # ERROR: Unnecessary Expr() wrapper
)

# WRONG - Unnecessary Expr() for number
snap_3 = TransformCSVParser(
    skip_lines=Expr("2")  # ERROR: Unnecessary Expr() wrapper
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
snap_0 = BinaryFileReader(label="Read CSV from S3", file_path="input.csv")

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
snap_4 = BinaryFileWriter(label="Write JSON to S3", filename="output.json")
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
snap_mapper = TransformMapper(label="Transform Data", transformations=TransformMapper.Transformations(mapping_table=[...]))
p.connect(src=snap_api, dst=snap_parser)
p.connect(src=snap_parser, dst=snap_mapper)

# CORRECT - Connect HTTP Client directly to transformation snaps
snap_api = APISuiteHTTPClient(label="Call REST API", method="GET", url="https://api.example.com/data")
snap_mapper = TransformMapper(label="Transform Data", transformations=TransformMapper.Transformations(mapping_table=[...]))
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
    label="Auth Request",
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
    label='API Key Auth', method='GET',
    url='https://api.example.com/v1/data',
    headers=[
        APISuiteHTTPClient.HeadersItem(header_name='X-API-Key', header_value='$_apiKey'),
        APISuiteHTTPClient.HeadersItem(header_name='Content-Type', header_value='application/json')
    ]
)

# Bearer Token
snap_0 = APISuiteHTTPClient(
    label='Bearer Token Auth', method='POST',
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
    label="Run Child Pipe",
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
    label="Run Child Pipe",
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
snap_0 = BinaryFileReader(label="Read CSV File", file_path="input.csv")
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
    label="Format Groups",
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$groupBy.continent"), target_path="$.continent"),  # Group key under $groupBy
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$countries.length"), target_path="$.country_count"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$countries"), target_path="$.countries"),
        ]
    ),
)

p.connect(src=snap_sort, dst=snap_group)
p.connect(src=snap_group, dst=snap_map)
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


### Rule 11: Lookup / Select / Execute Nest the Input Under `$original`

Several SnapLogic snaps do NOT pass their input document through unchanged. On output they emit a **new** document holding their own result fields, and attach the entire incoming document under a single top-level key named `original`. Every field the pipeline was carrying moves down one level.

This is the same class of bug as Rule 8 (`$groupBy`), but it bites harder: these are the most common enrichment snaps in database and legacy-ETL migrations, and a wrong path resolves to null rather than raising.

**Output shape after a database Lookup, on a match:**

```json
{
  "<output_field_1>": "...",
  "<output_field_2>": "...",
  "original": { "...the entire input document..." }
}
```

**Which snaps re-root, and what triggers it:**

| Snap family | Nests input under `original`? | Controlled by |
|---|---|---|
| Database `*Lookup` — `SQLServerLookup`, `OracleLookup`, `PostgreSQLLookup`, `SnowflakeLookup`, `RedshiftLookup`, `MySQLLookup`, `VerticaLookup`, `ExasolLookup`, `GoogleAlloyDBAlloyDBLookup` | **Always**, on every matched row | Nothing — unconditional |
| `*Select` and `*Execute` (SQL Server, Oracle, and the other JDBC packs) | Yes, **by default** | `pass_through`, which defaults to **True** here |
| `SalesforceLookup` | Yes, on either trigger | `correlation_id` set **or** `single_lookup=True` — independent paths; `single_lookup` alone is enough |
| `SalesforceSOSL` | Yes when enabled | that snap's own pass-through setting |
| LDAP Snaps (`LDAPLookup`, `LDAPSearch`, the write Snaps) and Active Directory Snaps (`ADSearch`, `ADListUsers`, `ADCreateEntry`, …) | Yes when enabled | `pass_through` / `pass_through_prop`, default **off**. `ActiveDirectoryAuthenticateUsers` defaults **on**. |
| `TransformInMemoryLookup`, `TransformJoin` | **No** | flat merge; the right view's label prefixes a colliding field name |

**`pass_through` on a Lookup snap does NOT control this.** On Lookup snaps that parameter is the platform's *"Pass-through on no lookup match"* (default **False**), and it decides only where an **unmatched** row goes — output view or error view. Setting `pass_through=False` does not flatten the document; the nesting still happens on every match.

On **no match** with `pass_through=True`: the input is nested under `original` as usual. What the Snap's *own* output fields look like on a miss is **unconfirmed — the two sources disagree**, so do not rely on either:

- The SQL Server documentation says *"If there are no results from the query, each output field will have a null value."*
- The source writes an empty document — `SimpleSqlLookupSnap` calls `newDocument(new LinkedHashMap<>())` with the input as the second argument, in both `jsql` and `jsqlv2`, and Oracle does not override that path — which would mean the output-field keys are absent rather than null.

Nobody has verified which wins at runtime. **The safe consequence either way:** `$original.<field>` reads correctly on a miss, so upstream fields are unaffected. Do not use `$someOutputField == null` to detect a miss, because that test works against the documented shape and silently fails against the coded one. With `pass_through=False` (the default) the row goes to the error view instead, which is the unambiguous way to handle misses.

`SalesforceLookup` does the same on a miss (`Lookup.java` 463-467 and 530-535), on both the single-lookup and batch paths. So an **uncorrelated batch lookup with `pass_through=True` emits mixed shapes** — flat on a match, nested on a miss. If you enable pass-through there, read both forms or set a `correlation_id` so the shape is consistent.

```python
# CORRECT — upstream fields under $original, the lookup's own output at the root
snap_lookup = SQLServerLookup(
    label="Lookup Product Key",
    output_fields=[SQLServerLookup.OutputFieldsItem(output_field="ProductKey")],
    # ... table, conditions, account
)

Item = TransformMapper.Transformations.MappingTableItem

snap_map = TransformMapper(
    label="Map Columns",
    transformations=TransformMapper.Transformations(
        mapping_table=[
            # Upstream fields moved down; nested paths move with them.
            Item(expression=Expr("$original.Id"), target_path="$.sfid"),
            Item(expression=Expr("$original.ProductCode"), target_path="$.productcode"),
            Item(expression=Expr("$original.Model_Code__r.Name"), target_path="$.model_code__c"),
            # The Lookup's OWN output field stays at the root.
            Item(expression=Expr("$ProductKey"), target_path="$.fp_product_key"),
        ]
    ),
)

p.connect(src=snap_lookup, dst=snap_map, src_view_id="output0", dst_view_id="input0")
```

**The rule in one line:** after a re-rooting snap, only that snap's declared output fields sit at the document root — everything else is under `$original`.

This applies to every downstream reference, not just Mappers: `FlowRouter` conditions, `FlowFilter` expressions, writer `updateCondition`s, and any expression-library call argument.

**How every row above was established, and how to settle a Snap that is not listed.** Two kinds of evidence. The second is what decides the cases the first is silent on:

1. **The Snap's documentation** — its **Output** row saying the input arrives under `original`. This is what confirms the JDBC `*Lookup` family, the `*Select` / `*Execute` family, and `SalesforceSOSL`.
2. **The write path in Snap_v4** — a *two-argument* `outputViews.write(document, originalData)` call. This is the nesting mechanism at SDK level, not a per-Snap convention: `OutBoundViews.write(Document, Object)` is documented in the JSDK as *"The new document will have an `original` key holding the original document to avoid data being overwritten when merging the data with original data."* This is what confirms the database Lookups (`SimpleSqlLookupSnap`), `SalesforceLookup`'s `processSingleLookup` path, and the LDAP and Active Directory Snaps — the last of which never mention nesting in their help text at all.

**So help-text silence is not evidence that a Snap merges flat.** If the docs do not mention `original`, read the write path before concluding anything; a two-argument write means it nests.

**When you are unsure about a snap**, call `pygen_get_snap_documentation` and read the **Output** row, looking for the word `original`. The platform uses **two different phrasings and they do not co-occur**, so searching for only one gives the wrong answer on half the family:

- *"...the corresponding input data under the `"original"` key"* — this is what **every JDBC `*Lookup`** uses (SQL Server, Oracle, PostgreSQL, MySQL, Redshift, AlloyDB).
- *"pass the input document to the output view under the key `original`"* — this is what the `*Select` / `*Execute` family and the Salesforce/Eloqua/OpenAPI Snaps use. **No Lookup carries this phrasing.**

Either phrasing means the Snap nests. Searching for the second one alone on a `*Lookup` finds nothing and leads to the exact wrong conclusion, on the family that nests unconditionally. Treat the word `original` in the Output row as the signal, not any one sentence.

**What `slpy translate` will and will not catch.** It warns when a Snap reads a bare `$field` downstream of a re-rooting Snap **whose output fields it can determine**, and it follows the document through Snaps that pass it on untouched (Router, Filter, Copy, Head, Sort, Unique). It stays silent — which is not a pass — after an `*Execute` Snap, when `output_fields` is omitted or expression-valued, past any other intermediate Snap, and when the reader sets a non-default `mapping_root`.

That silence is not spread evenly across the table. A declared `output_fields` list is what makes a Snap judgeable, so the check can cover the `*Lookup` and `*Select` rows, and **cannot cover `*Execute`, the LDAP Snaps or the Active Directory Snaps at all** — none of those declare one, so they are classified `never_judge` and will never produce a warning no matter how wrong the downstream read is. On those rows this rule is the only defence, which is the reason it enumerates them rather than telling you to rely on the translator.

### Rule 12: Name What the Canvas Shows

The user reads the canvas, not your code. Two things carry a name there: the snap's `label`, and the
label on each output view. Both are yours to set, and both are wrong by default.

On a refinement turn, apply this rule only to the snaps and branches the request adds or changes.
Never rename the others — the user already knows them by those names.

**Snap labels — name the step, not the snap.**

- **Two words, each ≤ 12 characters** (one word is fine too). That shape always renders in full;
  two full-length words plus the space is the 25-character ceiling.
  The canvas splits a label into two lines of at most 12 characters and cuts anything longer to 9
  characters plus `...`, so an over-long label does not just look untidy — its ending is gone.
- **A longer label fits only if its balanced split does.** The canvas breaks at the word boundary
  that makes the two lines closest in length, and each line must still be ≤ 12 characters.
  `Filter High Value` renders as `Filter` / `High Value`; `Format Manual Review` renders as
  `Format` / `Manual Re...`, because neither split keeps both halves within 12. When in doubt, use
  two words.
- Name what the step *does* to the data: `Filter Estimates`, `Split By Value`.
- Do NOT echo the snap type (`Mapper`, `Router Snap`, `CSV Parser Snap`), restate the pipeline's
  purpose on every snap (`Hotel Booking Revenue Mapper` inside a hotel-booking pipeline), or add step
  numbers unless two otherwise-identical steps need telling apart.
- Labels are unique within a pipeline — the canvas has no other way to tell two Mappers apart.

```python
# WRONG — reads like a class name; the canvas shows "Hotel / Booking R..."
snap_2 = TransformMapper(label='Hotel Booking Records Nightly Revenue Aggregation Mapper')
# CORRECT — 15 characters, two words, renders in full
snap_2 = TransformMapper(label='Nightly Revenue')
```

**Output view labels — name every branch, whatever the snap is.**

**Any** snap with 2+ non-error output views MUST carry a `src_view_label` on each of its
non-error outgoing `p.connect()` calls. Without one the canvas shows a bare `output0` / `output1` and
the user cannot tell the branches apart. The canvas draws every snap's view labels the same way, so
this is one rule for all of them — 87 snaps in the catalog can fan out, not just the obvious ones:
the copy family, every `*Select` / `*StoredProcedure` whose second view carries a result set or
output parameters, `MCPServerRouter`, `SOAPExecute`, the ML snaps. What counts is how many views
**this pipeline wires**, not the snap's maximum: several snaps (`TransformGroupByFields`,
`S3Browser`) accept a second output view but normally run with one, and a single-view snap needs no
label.

**A branch name is one word of ≤ 8 characters**, even when the user's own term is longer — shorten it
(`in_transit` → `Transit`, `exception` → `Issue`). The canvas draws it beside the branch connector,
and the next snap covers anything past about 8 characters — no `...`, the end is just hidden:

| branch name | canvas shows |
|---|---|
| `Archive` | `Archive` ✅ |
| `Aggregate` | `Aggregat` ❌ |
| `Batch Queue` | `Batch Queu` ❌ |

**Before picking a label, ask one question: does this snap name its own views?**

Look at the snap's parameters (`pygen_validate_snap_names` / `pygen_get_snap_parameters`). A property whose
name contains `output_view_name` means the view names are **configuration, not decoration**.

1. **It does** — the router family (`FlowRouter`, `FlowBinaryRouter`, `FlowHTTPRouter`, `ELTRouter`,
   `SparkSQLRouter`, `SparkSQL2XRouter`), `TransformDiff` (`output_view_name_prop`) and
   `Tableau910HyperParser` are the whole list today, but apply the test rather than the list. Here
   the `src_view_label` MUST be **byte-identical** to the configured name (see Mistake 20). The snap
   emits to that name, so the configured name carries the 8-character budget: pick
   `output_view_name` values that already fit (`AutoAdjudication` shows as `AutoAdju` — use
   `Auto`). If an existing one is too long, shorten the configuration and the label **together**,
   never one alone.
2. **It does not** — every other fan-out snap, `FlowCopy` first among them. The label is yours to
   choose: name where the branch goes (`Revenue`, `Archive`), or what the view carries when the snap
   fixes that (`Results`, `Params` on a stored procedure).

```python
snap_1 = FlowCopy(label='Fan Out Bookings')          # names no views -> labels are free
p.connect(src=snap_1, dst=snap_agg, src_view_id='output0', src_view_label='Revenue',
          dst_view_id='input0', src_output_type='document', dst_input_type='document')
p.connect(src=snap_1, dst=snap_archive, src_view_id='output1', src_view_label='Archive',
          dst_view_id='input0', src_output_type='document', dst_input_type='document')
```

**Two things this rule does not reach:**

- **Outgoing views only.** Never rename `dst_view_label` on a join, lookup or union input — that key
  selects the join path and prefixes the merged field names, so renaming it changes the output data.
  Error views (`error0`) are exempt too; leave them unlabelled.
- **A label another setting matches is a join key, not a display string.** Never shorten a pipeline
  label bound to a `FlowPipelineExecute(pipeline=...)` reference or a `pipeline_path`, a
  `TOOL_<capability>` name, or any label a skill tells you to carry verbatim (the agent and MCP
  bundles do). Those are contracts; this rule does not reach them.
