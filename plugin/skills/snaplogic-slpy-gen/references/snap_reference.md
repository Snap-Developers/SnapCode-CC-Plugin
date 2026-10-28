## 7. Snap Reference

### 7.1 Snap Categories by Pipeline Phase

SnapLogic pipelines typically follow a pattern: **READ -> PARSE -> TRANSFORM -> FORMAT -> WRITE**

#### 1. READ Phase (Data Ingestion)

Extract data from various sources:

**File Operations**:
- `BinaryFileReader`: Read files from filesystem, SFTP, S3, etc.
- `BinaryFilePoller`: Poll a directory for files matching a pattern
- `BinaryDirectoryBrowser`: List directory contents and file attributes

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
- `TransformJSONGenerator`: Generate documents from inline JSON — `editable_content='[{"k":"v"},...]'` (a JSON **string literal**, NOT `json.dumps(...)` — the agent isn't executing Python at SLPy-eval time), `array_elements_as_documents=True` to emit each array element as a separate document. **Preferred source-replacement snap when building a test segment** (data is inline, so no sample file or `file_path` to get wrong).

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
            output_view_name='high'
        ),
        FlowRouter.RoutesItem(
            expression=Expr('$amount <= 1000'),
            output_view_name='low'
        )
    ],
    first_match=True  # Stop after first match
)
```

**FlowRouter connections:** `output0` = first `RoutesItem`, `output1` = second, etc. — order must match route definition order. For readability, you can also use the route's `output_view_name` as `src_view_id` (e.g., `src_view_id='high'`) — slpy remaps it to the correct positional ID at translate time.

**MUST: every branch of a fan-out snap carries a `src_view_label`.** Any snap with 2+ non-error output views needs one on each non-error outgoing `p.connect()`, or the canvas renders the branch as a bare `output0`/`output1` and the user cannot tell the branches apart. `src_view_id` stays positional; the label is what the canvas shows.

Whether the label is free depends on one thing: does the snap name its own views? A parameter containing `output_view_name` says yes — the router family, `TransformDiff`, `Tableau910HyperParser` — and then `src_view_label` must repeat that configured name byte for byte, because the snap emits to it. Every other fan-out snap (`FlowCopy`, the `*Select` / `*StoredProcedure` result-set views, `MCPServerRouter`, the ML snaps) leaves the label to you: name where the branch goes (`'Revenue'`, `'Archive'`) or what it carries (`'Results'`). See Rule 12 in `critical_rules.md`.

```python
# Route names match between the snap definition and the connect call
FlowRouter(routes=[FlowRouter.RoutesItem(expression=Expr('$amount > 1000'), output_view_name='high')])
p.connect(src=snap_router, dst=snap_hv, src_view_id='output0', src_view_label='high', ...)
```

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
    label='Enrich With JS',
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
    label='Filter High Value',
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


### 7.6 Document Re-Rooting Snaps (`$original`)

Most transform snaps hand the next snap a document whose fields sit where they were. A few do not: they emit a **new** document holding their own result fields and attach the entire input document under a top-level key named `original`.

```
input  { Id: "01t…", ProductCode: "RV1234", … }
           ↓  SQLServerLookup(output_fields=["ProductKey"])
output { ProductKey: 88213, original: { Id: "01t…", ProductCode: "RV1234", … } }
```

Downstream, only the re-rooting snap's declared output fields are at the root. Every field carried from upstream is `$original.<field>`.

| Re-roots | Does not re-root |
|---|---|
| `SQLServerLookup`, `OracleLookup`, `PostgreSQLLookup`, `SnowflakeLookup`, `RedshiftLookup`, `MySQLLookup`, `VerticaLookup`, `ExasolLookup`, `GoogleAlloyDBAlloyDBLookup` — always | `TransformInMemoryLookup`, `TransformJoin` — flat merge, right view's label prefixes a colliding name |
| `*Select`, `*Execute` — `pass_through` defaults to True | `TransformMapper` with `pass_through=True` — copies fields at the same level |
| `SalesforceLookup` — only with `correlation_id` set or `single_lookup=True` | |
| `SalesforceSOSL`, LDAP and Active Directory Snaps — when their pass-through setting is on (verified from source; their help text does not mention it) | |
| `LLMUtilities*FunctionGenerator` (Multi Pipeline, APIM, OpenAPI) — always, unless `aggregate_input=True`, which emits no `original` at all. Chaining several adds exactly **one** level in total, not one each: each generator unwraps an existing `original` before re-wrapping | |
| `<Provider>PromptGenerator` — **conditionally**, see below | |

A prompt generator's `advanced_mode` ("Advanced prompt output") decides both what it emits and whether it re-roots. The snap's own help text does not cover it; the worked agent example is in the `agent-pipelines` skill, which restates this table so it stands alone — keep the two in step:

| `advanced_mode` | input state | output | nesting added |
|---|---|---|---|
| `False` | any | `{prompt: "<rendered string>"}`, upstream under `original` | **+1** |
| `True` | no `messages` key yet | `{messages: [msg]}`, upstream under `original` | **+1** |
| `True` | already has `messages` | appends to that array and re-roots its own expressions to `$original`; **keeps only `{messages, original}`** and discards every other top-level field | **0** |

Two traps follow.

A `True` generator placed downstream of a function generator **deletes `$tools`**.

And a `True` generator's mustache template resolves in whichever of the two `True` rows above applies to **its own input** — this is the part that gets misread. No `messages` key yet: it resolves against the document root, so it must spell out whatever nesting upstream already added (after an `advanced_mode=False` generator, that means `{{{original.msg}}}`, not `{{{msg}}}`). A `messages` key already present: it re-roots to `$original`, cancelling one level, so the same field is a bare `{{{msg}}}`. A generator only ever changes its own scope, never the next snap's. Both cases worked end to end: the `agent-pipelines` skill.

Do not confuse the two meanings of "pass through". On `TransformMapper` it means *keep the unmapped fields*. On a Lookup it means *route unmatched rows to the output view instead of the error view* — it does not control the nesting, which is unconditional.

Full rule, examples, and the no-match behaviour: **Rule 11** in `references/critical_rules.md`. Failure signature: **Mistake 21** in `references/anti_patterns.md`.
