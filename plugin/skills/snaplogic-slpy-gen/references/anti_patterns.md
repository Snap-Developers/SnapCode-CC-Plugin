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
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression="Date.now()", target_path="$.timestamp"),  # Function call without Expr()
        ]
    ),
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
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("Date.now()"), target_path="$.timestamp"),  # Expr required for function
        ]
    ),
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
2. pygen_validate_snap_names([ALL candidate snaps], do_get_parameters=True)   # names + params in ONE call
3. pygen_get_snap_documentation([connectivity_snaps_only])
4. Generate with available information
```

### Mistake 5: Python Concatenation Instead of SnapLogic Expression

**WRONG:**
```python
snap_0 = BinaryFileReader(
    file_path=_environment + "/file.csv"  # Python concatenation
)
```

**CORRECT:**
```python
snap_0 = BinaryFileReader(
    file_path=Expr("_environment + '/file.csv'")  # SnapLogic expression
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
    retries=Expr("3")  # Unnecessary Expr() for number
)
```

**CORRECT:**
```python
snap_0 = BinaryFileWriter(
    filename='output.json',  # Plain string - no Expr()
    retries=3  # Plain number - no Expr()
)
```

### Mistake 12: Skipping slpy translate Validation

**WRONG:** Generate SLPy code → deliver without running `slpy translate`.

**CORRECT:**
```
1. Generate SLPy code
2. cd <pipeline_dir> && slpy translate -src pipeline.py -dest pipeline.slp -strict -expr
3. Fix EVERY error the run reported (under -strict they are all fatal — no .slp is
   written) in ONE pass → re-translate. Normally one extra round, not one per error.
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
    transformations=TransformMapper.Transformations(
        mapping_table=[
            # DUPLICATES library logic inline instead of calling lib.helpers.*
            TransformMapper.Transformations.MappingTableItem(expression=Expr("'MSG-' + $timestamp.toLocaleDateTimeString({\"format\": \"yyyyMMddHHmmss\"}) + '-' + Math.random().toString(16).substring(2, 10).toUpperCase()"), target_path="$.msg_id"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("record.currency == null ? 'GBP' : (record.currency.toUpperCase() == 'GBP' ? 'GBP' : ...)"), target_path="$['@Ccy']"),
        ]
    ),
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
    transformations=TransformMapper.Transformations(
        mapping_table=[
            # Use library functions instead of duplicating logic
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.helpers.generate_message_id($timestamp)"), target_path="$.msg_id"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.helpers.normalize_currency(record.currency)"), target_path="$['@Ccy']"),
        ]
    ),
)
```

**Why this matters:**
- Expression libraries exist to centralize and reuse complex logic
- Duplicating logic inline defeats the purpose of the library
- Makes maintenance harder (changes needed in multiple places)
- Test pipelines verify library functions -- production must use the same functions
- Docstring becomes misleading if it documents functions that aren't actually used

### Mistake 15: Modifying Production Pipeline for Testing

> Note: when you do choose to exec (recommended for real transform logic — see Checkpoint 7) and a source/sink snap can't execute locally or makes a live call (Salesforce/Snowflake/DB, `APISuiteHTTPClient`), build a test segment so you can still exec offline and reproducibly. This mistake covers how to do it correctly.

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
- snap_0: APISuiteHTTPClient -> TransformJSONGenerator (inline sample docs)

All transformation snaps are IDENTICAL to production pipeline.
"""

# snap_0 replacement: inline JSON generator instead of the API call.
# PREFERRED over a file reader — the data is embedded, so there's no separate
# sample file to write and no file_path param to get wrong (a common source of
# "reader emits 0 docs" churn). editable_content is a JSON STRING literal.
snap_0 = TransformJSONGenerator(
    editable_content='[{"name":{"common":"Germany"},"continents":["Europe"]},'
                     '{"name":{"common":"Japan"},"continents":["Asia"]}]',
    array_elements_as_documents=True,
)
# ... all remaining transformation snaps IDENTICAL to production ...
# (Fall back to BinaryFileReader(file_path='sample.jsonl') + TransformJSONParser
#  ONLY when a downstream snap genuinely needs binary/CSV input.)
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
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$continent"), target_path="$.continent"),  # null on platform
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$countries.length"), target_path="$.count"),
        ]
    ),
)
```

**CORRECT:**
```python
# Group-by field referenced under $groupBy -- works on the platform
snap_map = TransformMapper(
    label="Summarize by Continent",
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$groupBy.continent"), target_path="$.continent"),  # Correct path
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$countries.length"), target_path="$.count"),
        ]
    ),
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

### Mistake 20: A fan-out branch left with no `src_view_label` on the connection

When a snap has more than one output view, the canvas labels each branch with that view's label. A `p.connect(...)` that carries no `src_view_label` leaves the branch reading `output0` / `output1`, and the user cannot tell the branches apart.

This bites hardest on routers, where a `FlowRouter.RoutesItem` already declares an `output_view_name`: the route has a perfectly good name and it silently fails to reach the canvas. But it applies to **every** snap that fans out — 87 of them in the catalog — and `FlowCopy` most of all, since nothing else names its branches. Naming router branches while leaving copy branches bare is the inconsistency users report.

**WRONG — `output_view_name` set on the route, but `src_view_label` missing on the connect:**
```python
snap_router = FlowRouter(
    label='Price Tier Router',
    first_match=True,
    routes=[
        FlowRouter.RoutesItem(expression=Expr('$price >= 100'), output_view_name='premium'),
        FlowRouter.RoutesItem(expression=Expr('$price < 100'),  output_view_name='budget'),
    ],
)
# Branch labels lost on the canvas — UI shows "output0"/"output1"
p.connect(src=snap_router, dst=snap_premium, src_view_id='output0', dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
p.connect(src=snap_router, dst=snap_budget,  src_view_id='output1', dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
```

**CORRECT — every routed connection carries `src_view_label` matching the route's `output_view_name`:**
```python
p.connect(src=snap_router, dst=snap_premium,
          src_view_id='output0', src_view_label='premium',
          dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
p.connect(src=snap_router, dst=snap_budget,
          src_view_id='output1', src_view_label='budget',
          dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
```

**WRONG — a copy snap's branches left bare (the same mistake, no route name involved):**
```python
snap_copy = FlowCopy(label='Fan Out Bookings')
# Canvas shows "output0" and "output1" — nothing says which branch is which
p.connect(src=snap_copy, dst=snap_revenue, src_view_id='output0', dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
p.connect(src=snap_copy, dst=snap_archive, src_view_id='output1', dst_view_id='input0',
          src_output_type='document', dst_input_type='document')
```

**CORRECT — each branch names where it goes:**
```python
p.connect(src=snap_copy, dst=snap_revenue, src_view_id='output0', src_view_label='Revenue',
          dst_view_id='input0', src_output_type='document', dst_input_type='document')
p.connect(src=snap_copy, dst=snap_archive, src_view_id='output1', src_view_label='Archive',
          dst_view_id='input0', src_output_type='document', dst_input_type='document')
```

**Rule:** every non-error outgoing connection from a snap with 2+ output views sets a `src_view_label`. `src_view_id` stays positional (`output0`, `output1`, …); the label is what the canvas shows.

Check the snap's parameters for a property containing `output_view_name` before choosing the label. If it has one — the router family, `TransformDiff`, `Tableau910HyperParser` — the label MUST be that configured string, byte for byte. A label that disagrees with the name the snap emits to is not merely cosmetic: it can cost documents at runtime. If the configured name is too long for the canvas, shorten the configuration and the label together, never one alone. If it has none (`FlowCopy` and the other 79 fan-out snaps), the label is free — name the branch's destination or what the view carries.

---


### Mistake 21: Reading Upstream Fields at Root Level After a Lookup / Select / Execute

**WRONG:**
```python
# Every upstream field read at the document root -- all resolve to null on the platform
snap_lookup = SQLServerLookup(
    label="Lookup Product Key",
    output_fields=[SQLServerLookup.OutputFieldsItem(output_field="ProductKey")],
)

snap_map = TransformMapper(
    label="Map Columns",
    null_safe_access=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$Id != null ? $Id : undefined"), target_path="$.sfid"),  # null
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$ProductCode != null ? $ProductCode : undefined"), target_path="$.productcode"),  # null
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$ProductKey"), target_path="$.fp_product_key"),  # correct
        ]
    ),
)

p.connect(src=snap_lookup, dst=snap_map, src_view_id="output0", dst_view_id="input0")
```

**CORRECT:**
```python
snap_map = TransformMapper(
    label="Map Columns",
    null_safe_access=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$original.Id != null ? $original.Id : undefined"), target_path="$.sfid"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$original.ProductCode != null ? $original.ProductCode : undefined"), target_path="$.productcode"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$ProductKey"), target_path="$.fp_product_key"),  # the lookup's own output stays at the root
        ]
    ),
)
```

**Why this matters:**
- A Lookup snap emits its own output fields at the root and nests the entire input document under `original` (see Rule 11). `$Id` resolves to null because the value lives at `$original.Id`.
- **This fails silently.** With `null_safe_access=True` and a `!= null ? ... : undefined` guard — the shape a migration generator naturally produces from a field-mapping spec — a wrong path yields `undefined` and the column is simply omitted from the write. The pipeline translates, imports, and runs. Rows land empty.
- When the target's key column is one of the dropped fields, the write loses its key as well, so an upsert cannot match and the failure is total rather than partial.
- Legacy ETL platforms (Informatica, DataStage, BizTalk) enrich a row **in place** — their lookups do not re-root. Transcribing a source field map one-to-one into a Mapper placed after a SnapLogic Lookup reproduces the source layout and is wrong every time. Re-root the paths as part of the translation, not afterwards.
- `slpy exec` will not catch this for database lookups — they are outside the executable snap set. Rely on Rule 11 and Checkpoint 2 instead.
