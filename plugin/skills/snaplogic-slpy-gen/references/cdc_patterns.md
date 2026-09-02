# Change Data Capture (CDC) Patterns for SLPy Pipelines

Comprehensive guide to implementing Change Data Capture in SnapLogic pipelines using SLPy. Documents two proven approaches: **TransformDiff-based** (recommended) and **hash-based** (alternative).

---

## Table of Contents

1. [Overview](#overview)
2. [Pattern Selection Guide](#pattern-selection-guide)
3. [Pattern 1: TransformDiff-Based CDC (RECOMMENDED)](#pattern-1-transformdiff-based-cdc-recommended)
4. [Pattern 2: Hash-Based CDC (Alternative)](#pattern-2-hash-based-cdc-alternative)
5. [Testing CDC Pipelines](#testing-cdc-pipelines)
6. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Overview

Change Data Capture (CDC) is a pattern for identifying and processing only the records that have changed since the last pipeline run. CDC pipelines compare a current dataset against a prior snapshot and classify each record as INSERT, UPDATE, DELETE, or UNCHANGED, then route the results accordingly.

**TransformDiff-based CDC is the recommended approach** for most SnapLogic CDC pipelines.

### Approach Comparison

| Approach | DELETE Detection | State Management | Complexity | Best For |
|----------|-----------------|------------------|------------|----------|
| **TransformDiff** (Recommended) | Yes — native | Prior snapshot file (CSV/JSON) | Low — uses built-in snap | Most CDC scenarios; file-based data; any case needing DELETE detection |
| **Hash-Based** | No — only INSERT/UPDATE | Hash state file (JSON) | Medium — requires hash computation, join, expand logic | When TransformDiff is unavailable; when you need custom change logic |
| **Timestamp-Based** | No | None (relies on source) | Low | When source has reliable `updated_at` column |

### Key Advantages of TransformDiff

- **Native DELETE detection**: Identifies records present in the prior snapshot but absent from the current data
- **No hash computation**: Compares records field-by-field without SHA-256 overhead
- **Four output views**: Separate streams for Deletions, Insertions, Modified, and Unmodified records
- **Simpler pipeline**: Fewer snaps needed compared to hash-based approach
- **Proven in production**: Verified in production SnapLogic pipelines

---

## Pattern Selection Guide

### Decision Tree

```
Need CDC? ──Yes──> Can store prior snapshot file? ──Yes──> TransformDiff (Pattern 1)
                                                    │
                                                    No──> Hash-Based (Pattern 2)
                                                          (uses JSON state file instead)

Need DELETE detection? ──Yes──> TransformDiff (Pattern 1)
                         │
                         No──> Either pattern works

Custom change logic needed? ──Yes──> Hash-Based (Pattern 2)
(e.g., ignore certain fields)  │
                                No──> TransformDiff (Pattern 1)
```

**Default choice: Use TransformDiff unless you have a specific reason not to.**

---

## Pattern 1: TransformDiff-Based CDC (RECOMMENDED)

Uses SnapLogic's native `TransformDiff` snap to compare current data against a prior snapshot file and produce four classified output streams.

### 3.1 Architecture

#### Full Mode Flow

```
[Source Query] → [Lowercase Keys] → [Masking] → [FlowCopy]
                                                      |
                                         [S3 Branch] ←+→ [FTP Branch]
                                         JSONFormatter    RemoveCDCCols
                                              ↓               ↓
                                         S3Upload        CSVFormatter
                                                              ↓
                                                         FileWriter (FTP)
```

#### Delta Mode Flow

```
[Source Query] → [Lowercase Keys] → [FlowRouter: Full/Delta]
                                           |
              [Full Path] ←────────────────+────────────────→ [Delta Path]
              Masking → FlowCopy → S3+FTP                     FlowCopy
                                                                  |
                                              [TransformDiff] ←───+───→ [GroupByFields + Merge for FTP]
                                              (current vs prior)
                                                  |
                              ┌──────────┬────────┴────────┬──────────┐
                          Deletions  Insertions       Modified    Unmodified
                              ↓          ↓                ↓           ↓
                          +DELETE    +INSERT          +UPDATE     Script(discard)
                              ↓          ↓                ↓
                              └──────────┴────────────────┘
                                         ↓
                                     [FlowUnion]
                                         ↓
                                     [Masking]
                                         ↓
                                    [JSONFormatter]
                                         ↓
                                    [S3Upload Delta]

[Prior Snapshot Loading]:
DirectoryBrowser → FileReader → CSVParser → FlowFilter(isDelta?) → Sort → TransformDiff(inputOriginal)
```

### 3.2 TransformDiff Snap Configuration

The `TransformDiff` snap compares two sorted input streams and classifies records into four output views.

```python
snap_diff = TransformDiff(
    label="Diff",
    sort_paths=[TransformDiff.SortPathsItem(sort_path="$id")],
    sort_order="Ascending",
    output_view_map_prop=[
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Deletions",
            output_view_type_prop="DELETIONS"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Insertions",
            output_view_type_prop="INSERTIONS"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Modified",
            output_view_type_prop="MODIFIED"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Unmodified",
            output_view_type_prop="UNMODIFIED"
        ),
    ],
)
```

**Critical configuration details:**

| Property | Value | Notes |
|----------|-------|-------|
| `sort_paths` | Primary key field(s) | Both input streams MUST be sorted by this field |
| `sort_order` | `"Ascending"` | Must match the sort order of both input streams |
| `output_view_map_prop` | 4 views | All four types should be mapped even if you only use some |

**Input views** (connection targets):

| View ID | Purpose |
|---------|---------|
| `inputOriginal` | Prior snapshot data (the "old" data) |
| `inputNew` | Current data (the "new" data) |

**Output views** (connection sources):

| View ID | Contains |
|---------|----------|
| `outputDeletions` | Records in Original but NOT in New |
| `outputInsertions` | Records in New but NOT in Original |
| `outputModified` | Records in both, but with different field values |
| `outputUnmodified` | Records identical in both streams |

### 3.3 Change Type Labeling

Each TransformDiff output view feeds into a TransformMapper that adds `CDC_TIMESTAMP` and `CDC_OPERATION` fields. Use `pass_through=True` to preserve all original fields.

#### DELETE Label

```python
snap_label_delete = TransformMapper(
    label="Delete Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    "pipe.startTime.toLocaleDateTimeString("
                    "{'timeZone':'UTC',\"format\":\"yyyy-MM-dd'T'HH:mm:ss.SSS\"})"
                    "+Date.now().getMilliseconds()+'Z'"
                ),
                target_path="CDC_TIMESTAMP",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"DELETE"',
                target_path="CDC_OPERATION",
            ),
        ],
    ),
)
```

#### INSERT Label

```python
snap_label_insert = TransformMapper(
    label="Insert Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    "pipe.startTime.toLocaleDateTimeString("
                    "{'timeZone':'UTC',\"format\":\"yyyy-MM-dd'T'HH:mm:ss.SSS\"})"
                    "+Date.now().getMilliseconds()+'Z'"
                ),
                target_path="CDC_TIMESTAMP",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"INSERT"',
                target_path="CDC_OPERATION",
            ),
        ],
    ),
)
```

#### UPDATE Label

```python
snap_label_update = TransformMapper(
    label="Update Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    "pipe.startTime.toLocaleDateTimeString("
                    "{'timeZone':'UTC',\"format\":\"yyyy-MM-dd'T'HH:mm:ss.SSS\"})"
                    "+Date.now().getMilliseconds()+'Z'"
                ),
                target_path="CDC_TIMESTAMP",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"UPDATE"',
                target_path="CDC_OPERATION",
            ),
        ],
    ),
)
```

#### Union

Merge the three labeled change streams into one:

```python
snap_union = FlowUnion(label="Union")
```

Connect DELETE, INSERT, and UPDATE labeled outputs to separate input views on the Union:

```python
p.connect(src=snap_label_delete, dst=snap_union,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_insert, dst=snap_union,
          src_view_id="output0", dst_view_id="input1",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_update, dst=snap_union,
          src_view_id="output0", dst_view_id="input101",
          src_output_type="document", dst_input_type="document")
```

### 3.4 Prior Snapshot Management

The prior snapshot is a file (typically CSV) stored from the previous full run. Load it using a DirectoryBrowser → FileReader → CSVParser chain.

```python
snap_dir_browser = BinaryDirectoryBrowser(
    label="Directory Browser",
    directory="lib.cdc_config.Account.Details.DIRECTORY_BROWSER.Directory",
    filter="lib.cdc_config.Account.Details.DIRECTORY_BROWSER.File_Filter",
    ignore_empty_result=True,
)

snap_file_reader = BinaryFileReader(
    label="File Reader",
    file_path="$Path",
    execution_mode="Execute only",
)

snap_csv_parser = TransformCSVParser(
    label="Parse Prior Snapshot",
    delimiter="~|",
    escape_char="\\",
    contains_header=False,
    ignore_empty_data=True,
    execution_mode="Execute only",
)
```

**Why DirectoryBrowser?** It gracefully handles missing files (first run) when `ignore_empty_result=True` — the pipeline continues with no prior data, so all current records appear as Insertions.

### 3.5 Full/Delta Mode Routing

Use an expression library flag to control whether the pipeline runs in Full or Delta mode.

```python
snap_router = FlowRouter(
    label="Full/Delta",
    routes=[
        FlowRouter.RoutesItem(
            expression='lib.cdc_config.Delta == "N"',
            output_view_name="Full"
        ),
        FlowRouter.RoutesItem(
            expression='lib.cdc_config.Delta == "Y"',
            output_view_name="Delta"
        ),
    ],
)
```

The FlowFilter on the prior snapshot loading path ensures prior data only flows when in delta mode:

```python
snap_check_delta = FlowFilter(
    label="Check Delta",
    filter_expression='lib.cdc_config.Delta == "Y"',
    execution_mode="Execute only",
)
```

### 3.6 Expression Library Configuration

The expression library (`.expr` file) centralizes environment-specific configuration. This pattern uses the library for account details, obfuscation settings, and helper functions.

```javascript
{
    "Account":
    {
        "Details":
        {
            "Bucket":
            {
                "DEV": "my-bucket-dev",
                "QA": "my-bucket-qa",
                "PROD": "my-bucket-prod"
            },
            "FULL_S3":
            {
                "Object_Key": "Landing/Schema.Table/.Table/",
                "Prefix_Date": Date.now().toLocaleDateTimeString({"timeZone":"UTC","format":"yyyyMMddHHmmss"}),
                "File_Name": "my_table.ndjson"
            },
            "DELTA_S3":
            {
                "Object_Key": "Landing/Schema.Table/.Table_ct/",
                "Prefix_Date": Date.now().toLocaleDateTimeString({"timeZone":"UTC","format":"yyyyMMddHHmmss"}),
                "File_Name": "my_table.ndjson"
            },
            "FTP":
            {
                "File_Name": "file:///data/exports/my_table_Full.txt"
            },
            "DIRECTORY_BROWSER":
            {
                "Directory": "file:///data/exports/",
                "File_Filter": "my_table_Full.txt"
            }
        }
    },
    "Obfuscation_IND":
    {
        "DEV": "Y",
        "QA": "N",
        "PROD": "N"
    },
    "Delta": "N",
    maskData : x => x.replace(/[A-Z]/g, 'A').replace(/[a-z ]/g, x => (x == 'z' ? 'j' : 'a')).replace(/[0-9]/g, 9),

    getOrgName : () => pipe.projectPath.split('/')[1].toUpperCase()
    ,getEnv : () => this.getOrgName().split('_')[1]
    ,getEnvValue : (key) => this.get(key).get(this.getEnv())
}
```

**Key patterns:**

| Pattern | Purpose | Example Usage |
|---------|---------|---------------|
| `Bucket` per environment | Environment-specific S3 buckets | `lib.cdc_config.Account.Details.Bucket.get(lib.cdc_config.getEnv())` |
| `Obfuscation_IND` per environment | Control masking per environment | `lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N"` |
| `Delta` flag | Full vs Delta mode toggle | `lib.cdc_config.Delta == "Y"` |
| `maskData` function | Data obfuscation | `lib.cdc_config.maskData($field)` |
| `getOrgName()` / `getEnv()` | Derive environment from project path | See below |

> **WARNING — `this.fn()` limitation**: The expression library above uses `this.getOrgName()` and `this.get()` for cross-references. These work in the SnapLogic platform but **return null in `slpy exec`** (see SKILL.md Gotcha 9). For `slpy exec` compatibility, use `lib.cdc_config.getEnv()` instead of `this.getEnv()`, or inline the logic. When generating pipelines, prefer `lib.<name>.fn()` syntax in snap expressions that reference library functions.

### 3.7 Data Masking

The masking mapper conditionally obfuscates fields based on the environment's `Obfuscation_IND` setting.

```python
snap_masking = TransformMapper(
    label="Masking Data",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    'lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N"'
                    ' ? $id : lib.cdc_config.maskData($id)'
                ),
                target_path="$id",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    'lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N"'
                    ' ? $name : lib.cdc_config.maskData($name)'
                ),
                target_path="$name",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    'lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N"'
                    ' ? $status : lib.cdc_config.maskData($status)'
                ),
                target_path="$status",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    'lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N"'
                    ' ? $category : lib.cdc_config.maskData($category)'
                ),
                target_path="$category",
            ),
            # Repeat for each field that needs masking
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_TIMESTAMP",
                target_path="$CDC_TIMESTAMP",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_OPERATION",
                target_path="$CDC_OPERATION",
            ),
        ],
    ),
)
```

### 3.8 Output Formatting

#### S3 Output (NDJSON)

```python
snap_json_fmt = TransformJSONFormatter(
    label="NDJSON Format",
    json_lines=True,
    pretty_print=False,
    ignore_empty_stream=True,
)

snap_s3_upload = S3Upload(
    label="S3 Upload",
    bucket="lib.cdc_config.Account.Details.Bucket.get(lib.cdc_config.getEnv())",
    object_key=(
        "lib.cdc_config.Account.Details.FULL_S3.Object_Key"
        "+lib.cdc_config.Account.Details.FULL_S3.Prefix_Date"
        "+lib.cdc_config.Account.Details.FULL_S3.File_Name"
    ),
    pm_account=Expr('lib.my_shared_accounts.S3_Account.get(lib.my_shared_accounts.getEnv())'),
)
```

#### FTP Output (CSV)

For FTP output, CDC columns (`CDC_TIMESTAMP`, `CDC_OPERATION`) are typically removed before writing:

```python
snap_remove_cdc_cols = TransformMapper(
    label="Remove CDC Columns",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_TIMESTAMP", target_path=None
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_OPERATION", target_path=None
            ),
        ],
    ),
)

snap_csv_fmt = TransformCSVFormatter(
    label="CSV Formatter",
    delimiter="~|",
    write_header=False,
    quote_mode="ALL",
    quote_character=None,
    newline_character="LF",
    escape_char="\\",
)

snap_ftp_writer = BinaryFileWriter(
    label="FTP Writer",
    filename="lib.cdc_config.Account.Details.FTP.File_Name",
    file_action="OVERWRITE",
)
```

> **Note:** The `~|` delimiter is shown here as one example. Use whatever delimiter your downstream system requires.

### 3.9 Consuming Unmodified Output (CRITICAL)

The `outputUnmodified` view of TransformDiff **must be consumed** or the pipeline will hang. Use a Script snap to read and discard the records:

```python
snap_consume = Script(
    label="Consume Unmodified",
    language="Javascript",
    editable_content=(
        'try { load("nashorn:mozilla_compat.js"); } catch(e) { }\n'
        'importPackage(com.snaplogic.scripting.language);\n'
        'importClass(java.util.LinkedHashMap);\n'
        'var impl = {\n'
        '    input: input, output: output, error: error, log: log,\n'
        '    execute: function() {\n'
        '        while (this.input.hasNext()) {\n'
        '            try { var inDoc = this.input.next(); }\n'
        '            catch (err) {\n'
        '                var errDoc = new LinkedHashMap();\n'
        '                errDoc.put("error", err);\n'
        '                this.error.write(errDoc);\n'
        '            }\n'
        '        }\n'
        '    },\n'
        '    cleanup: function() {}\n'
        '};\n'
        'var hook = new com.snaplogic.scripting.language.ScriptHook(impl);\n'
    ),
)
```

This script reads every document from the input but does not write to the output — effectively discarding the Unmodified records.

### 3.10 Advanced: Merge Delta with Full Data for FTP Update

When the FTP output requires a complete file (not just deltas), you need to merge delta records back into the full dataset. This uses a GroupByN → GroupByFields → Merge pattern.

#### How It Works

1. Delta records from S3 upload pass-through are collected via `GroupByN`
2. Current full data is sorted and grouped by primary key via `GroupByFields`
3. A `TransformJoin` (Merge type) combines the two streams
4. A `TransformJSONSplitter` extracts the full data array
5. The merged result goes through masking and CSV formatting to FTP

```python
# Collect delta records (from S3 upload pass-through)
snap_group_n = TransformGroupByN(
    label="Group By N",
    target_field="Filter",
    group_size=10,
)

# Sort current full data by primary key
snap_sort_full = TransformSort(
    label="Sort Full Data",
    sort_paths=[TransformSort.SortPathsItem(sort_path="$id", sort_order_ind="global")],
    sort_order="ascending",
    null_safe_access=True,
)

# Group full data by primary key
snap_group_fields = TransformGroupByFields(
    label="Group By Fields",
    fields=[TransformGroupByFields.FieldsItem(field="$id")],
    target_field="FullData",
)

# Extract FullData array
snap_extract_full = TransformMapper(
    label="Extract Full Data",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression="$FullData",
                target_path="$FullData",
            )
        ],
    ),
)

# Merge: delta (input0) + full data (input1)
snap_merge = TransformJoin(
    label="Merge",
    join_type="Merge",
    sorted_streams="Ascending",
)

# Split merged FullData array back to individual records
snap_splitter = TransformJSONSplitter(
    label="Split Data",
    path="$FullData",
    include_parents=False,
)
```

#### Connections for Merge Pattern

```python
# S3 upload pass-through → GroupByN → Merge (input0)
p.connect(src=snap_s3_upload, dst=snap_group_n,
          src_view_id="output103", dst_view_id="input0",  # pass-through view
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_group_n, dst=snap_merge,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# FlowCopy output → Sort → GroupByFields → Extract → Merge (input1)
p.connect(src=snap_delta_copy, dst=snap_sort_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_sort_full, dst=snap_group_fields,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_group_fields, dst=snap_extract_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_extract_full, dst=snap_merge,
          src_view_id="output0", dst_view_id="input1",
          src_output_type="document", dst_input_type="document")

# Merge → Splitter → Masking → CSV → FTP
p.connect(src=snap_merge, dst=snap_splitter,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_splitter, dst=snap_masking_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
```

### 3.11 Snap Configurations Reference

All snaps used in the TransformDiff CDC pattern:

| Snap | Label | Key Configuration |
|------|-------|-------------------|
| `SnowflakeExecute` | Source Query | `sql_statement` with `ORDER BY id`; `pm_account` from shared accounts lib |
| `TransformMapper` | Lowercase Keys | `$.mapKeys((value, key) => key.toLowerCase())` |
| `FlowRouter` | Full/Delta | Routes on `lib.cdc_config.Delta` flag |
| `BinaryDirectoryBrowser` | Directory Browser | `directory`/`filter` from expr lib; `ignore_empty_result=True` |
| `BinaryFileReader` | File Reader | `file_path="$Path"` (from DirBrowser output) |
| `TransformCSVParser` | Parse Prior Snapshot | `delimiter`, `contains_header=False`, `ignore_empty_data=True` |
| `FlowFilter` | Check Delta | `filter_expression='lib.cdc_config.Delta == "Y"'` |
| `TransformSort` | Sort (prior & current) | `sort_paths` on primary key; `sort_order="ascending"` |
| `FlowCopy` | Copy Delta | Splits current data for TransformDiff and FTP merge |
| `TransformDiff` | Diff | `sort_paths` on primary key; 4 output views |
| `TransformMapper` | Delete/Insert/Update Action | `pass_through=True`; adds `CDC_TIMESTAMP` + `CDC_OPERATION` |
| `Script` | Consume Unmodified | Reads and discards Unmodified records |
| `FlowUnion` | Union | Merges DELETE + INSERT + UPDATE streams |
| `TransformMapper` | Masking | Conditional obfuscation per environment |
| `TransformJSONFormatter` | NDJSON Format | `json_lines=True` for S3 |
| `S3Upload` | S3 Upload | `bucket`/`object_key` from expr lib |
| `TransformCSVFormatter` | CSV Formatter | `delimiter`, `write_header=False` for FTP |
| `BinaryFileWriter` | FTP Writer | `filename` from expr lib; `file_action="OVERWRITE"` |

### 3.12 Pipeline Connections

#### Prior Snapshot Loading (Delta mode only)

```python
# DirectoryBrowser → FileReader → CSVParser → FlowFilter → Sort → TransformDiff(inputOriginal)
p.connect(src=snap_dir_browser, dst=snap_file_reader,
          src_view_id="out", dst_view_id="input103",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_file_reader, dst=snap_csv_parser,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_csv_parser, dst=snap_check_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_check_delta, dst=snap_sort_prior,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_sort_prior, dst=snap_diff,
          src_view_id="output0", dst_view_id="inputOriginal",
          src_output_type="document", dst_input_type="document")
```

#### Source → Router

```python
# Source → Lowercase Keys → FlowRouter
p.connect(src=snap_source, dst=snap_lowercase,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_lowercase, dst=snap_router,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
```

#### Delta Path

```python
# Router(Delta) → FlowCopy
p.connect(src=snap_router, dst=snap_delta_copy,
          src_view_id="output1", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# FlowCopy output1 → TransformDiff(inputNew)
p.connect(src=snap_delta_copy, dst=snap_diff,
          src_view_id="output1", dst_view_id="inputNew",
          src_output_type="document", dst_input_type="document")

# TransformDiff outputs → Label mappers
p.connect(src=snap_diff, dst=snap_label_delete,
          src_view_id="outputDeletions", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_label_insert,
          src_view_id="outputInsertions", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_label_update,
          src_view_id="outputModified", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_consume,
          src_view_id="outputUnmodified", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Label mappers → Union
p.connect(src=snap_label_delete, dst=snap_union,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_insert, dst=snap_union,
          src_view_id="output0", dst_view_id="input1",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_update, dst=snap_union,
          src_view_id="output0", dst_view_id="input101",
          src_output_type="document", dst_input_type="document")

# Union → Masking → JSONFormatter → S3Upload (Delta)
p.connect(src=snap_union, dst=snap_masking_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_masking_delta, dst=snap_json_fmt_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_json_fmt_delta, dst=snap_s3_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
```

#### Full Path

```python
# Router(Full) → Masking → FlowCopy
p.connect(src=snap_router, dst=snap_masking_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_masking_full, dst=snap_full_copy,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# FlowCopy → S3 branch
p.connect(src=snap_full_copy, dst=snap_json_fmt_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_json_fmt_full, dst=snap_s3_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")

# FlowCopy → FTP branch (remove CDC columns → CSV → FileWriter)
p.connect(src=snap_full_copy, dst=snap_remove_cdc_cols,
          src_view_id="output1", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_remove_cdc_cols, dst=snap_csv_fmt,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_csv_fmt, dst=snap_ftp_writer,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
```

### 3.13 Complete Example

#### Expression Library (cdc_config.expr)

```javascript
{
    "Account":
    {
        "Details":
        {
            "Bucket":
            {
                "DEV": "my-bucket-dev",
                "QA": "my-bucket-qa",
                "PROD": "my-bucket-prod"
            },
            "FULL_S3":
            {
                "Object_Key": "Landing/MySchema.MyTable/.MyTable/",
                "Prefix_Date": Date.now().toLocaleDateTimeString({"timeZone":"UTC","format":"yyyyMMddHHmmss"}),
                "File_Name": "my_table.ndjson"
            },
            "DELTA_S3":
            {
                "Object_Key": "Landing/MySchema.MyTable/.MyTable_ct/",
                "Prefix_Date": Date.now().toLocaleDateTimeString({"timeZone":"UTC","format":"yyyyMMddHHmmss"}),
                "File_Name": "my_table.ndjson"
            },
            "FTP":
            {
                "File_Name": "file:///data/exports/my_table_Full.txt"
            },
            "DIRECTORY_BROWSER":
            {
                "Directory": "file:///data/exports/",
                "File_Filter": "my_table_Full.txt"
            }
        }
    },
    "Obfuscation_IND":
    {
        "DEV": "Y",
        "QA": "N",
        "PROD": "N"
    },
    "Delta": "N",
    maskData : x => x.replace(/[A-Z]/g, 'A').replace(/[a-z ]/g, x => (x == 'z' ? 'j' : 'a')).replace(/[0-9]/g, 9),

    getOrgName : () => pipe.projectPath.split('/')[1].toUpperCase()
    ,getEnv : () => this.getOrgName().split('_')[1]
    ,getEnvValue : (key) => this.get(key).get(this.getEnv())
}
```

#### Pipeline (cdc_transformdiff_pipeline.py)

```python
"""
Pipeline Name: CDC TransformDiff Example

Pipeline Summary:
Demonstrates TransformDiff-based CDC pattern with Full/Delta routing,
S3 and FTP output, environment-based data masking.

Data Flow:
  Full mode:  Source → Lowercase → Masking → FlowCopy → S3 + FTP
  Delta mode: Source → Lowercase → FlowRouter → FlowCopy →
              TransformDiff (current vs prior) → Label (DELETE/INSERT/UPDATE) →
              Union → Masking → S3 + FTP
"""

from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries

from slpy.modules.Snap.BinaryDirectoryBrowser import BinaryDirectoryBrowser
from slpy.modules.Snap.BinaryFileReader import BinaryFileReader
from slpy.modules.Snap.BinaryFileWriter import BinaryFileWriter
from slpy.modules.Snap.FlowCopy import FlowCopy
from slpy.modules.Snap.FlowFilter import FlowFilter
from slpy.modules.Snap.FlowRouter import FlowRouter
from slpy.modules.Snap.FlowUnion import FlowUnion
from slpy.modules.Snap.S3Upload import S3Upload
from slpy.modules.Snap.Script import Script
from slpy.modules.Snap.SnowflakeExecute import SnowflakeExecute
from slpy.modules.Snap.TransformCSVFormatter import TransformCSVFormatter
from slpy.modules.Snap.TransformCSVParser import TransformCSVParser
from slpy.modules.Snap.TransformDiff import TransformDiff
from slpy.modules.Snap.TransformJSONFormatter import TransformJSONFormatter
from slpy.modules.Snap.TransformMapper import TransformMapper
from slpy.modules.Snap.TransformSort import TransformSort

p = Pipeline(label='CDC TransformDiff Example')

# Expression libraries
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(path='cdc_config.expr', as_='cdc_config'),
])

# ── Source ──────────────────────────────────────────────────────────────────
snap_source = SnowflakeExecute(
    label="Source Query",
    sql_statement=(
        "SELECT id, name, status, category "
        "FROM MY_SCHEMA.MY_TABLE "
        "ORDER BY id"
    ),
    query_type="Auto",
    pass_through=True,
    pm_account=Expr('lib.my_shared_accounts.Snowflake_Account.get(lib.my_shared_accounts.getEnv())'),
)

# ── Lowercase Keys ─────────────────────────────────────────────────────────
snap_lowercase = TransformMapper(
    label="Lowercase Keys",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression="$.mapKeys((value, key) => key.toLowerCase())",
                target_path="$",
            )
        ],
    ),
)

# ── Full/Delta Router ──────────────────────────────────────────────────────
snap_router = FlowRouter(
    label="Full/Delta",
    routes=[
        FlowRouter.RoutesItem(
            expression='lib.cdc_config.Delta == "N"',
            output_view_name="Full",
        ),
        FlowRouter.RoutesItem(
            expression='lib.cdc_config.Delta == "Y"',
            output_view_name="Delta",
        ),
    ],
)

# ── Prior Snapshot Loading ─────────────────────────────────────────────────
snap_dir_browser = BinaryDirectoryBrowser(
    label="Directory Browser",
    directory="lib.cdc_config.Account.Details.DIRECTORY_BROWSER.Directory",
    filter="lib.cdc_config.Account.Details.DIRECTORY_BROWSER.File_Filter",
    ignore_empty_result=True,
)

snap_file_reader = BinaryFileReader(
    label="File Reader",
    file_path="$Path",
    execution_mode="Execute only",
)

snap_csv_parser = TransformCSVParser(
    label="Parse Prior Snapshot",
    delimiter="~|",
    escape_char="\\",
    contains_header=False,
    ignore_empty_data=True,
    execution_mode="Execute only",
)

snap_check_delta = FlowFilter(
    label="Check Delta",
    filter_expression='lib.cdc_config.Delta == "Y"',
    execution_mode="Execute only",
)

snap_sort_prior = TransformSort(
    label="Sort Prior Data",
    sort_paths=[TransformSort.SortPathsItem(sort_path="$id", sort_order_ind="global")],
    sort_order="ascending",
    null_safe_access=True,
    execution_mode="Execute only",
)

# ── TransformDiff ──────────────────────────────────────────────────────────
snap_diff = TransformDiff(
    label="Diff",
    sort_paths=[TransformDiff.SortPathsItem(sort_path="$id")],
    sort_order="Ascending",
    output_view_map_prop=[
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Deletions", output_view_type_prop="DELETIONS"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Insertions", output_view_type_prop="INSERTIONS"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Modified", output_view_type_prop="MODIFIED"
        ),
        TransformDiff.OutputViewMapPropItem(
            output_view_name_prop="Unmodified", output_view_type_prop="UNMODIFIED"
        ),
    ],
    execution_mode="Execute only",
)

# ── Change Type Labels ─────────────────────────────────────────────────────
_cdc_ts_expr = (
    "pipe.startTime.toLocaleDateTimeString("
    "{'timeZone':'UTC',\"format\":\"yyyy-MM-dd'T'HH:mm:ss.SSS\"})"
    "+Date.now().getMilliseconds()+'Z'"
)

snap_label_delete = TransformMapper(
    label="Delete Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=_cdc_ts_expr, target_path="CDC_TIMESTAMP"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"DELETE"', target_path="CDC_OPERATION"
            ),
        ],
    ),
    execution_mode="Execute only",
)

snap_label_insert = TransformMapper(
    label="Insert Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=_cdc_ts_expr, target_path="CDC_TIMESTAMP"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"INSERT"', target_path="CDC_OPERATION"
            ),
        ],
    ),
    execution_mode="Execute only",
)

snap_label_update = TransformMapper(
    label="Update Action",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=_cdc_ts_expr, target_path="CDC_TIMESTAMP"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"UPDATE"', target_path="CDC_OPERATION"
            ),
        ],
    ),
    execution_mode="Execute only",
)

# ── Consume Unmodified (CRITICAL — prevents pipeline hang) ─────────────────
snap_consume = Script(
    label="Consume Unmodified",
    language="Javascript",
    editable_content=(
        'try { load("nashorn:mozilla_compat.js"); } catch(e) { }\n'
        'importPackage(com.snaplogic.scripting.language);\n'
        'importClass(java.util.LinkedHashMap);\n'
        'var impl = {\n'
        '    input: input, output: output, error: error, log: log,\n'
        '    execute: function() {\n'
        '        while (this.input.hasNext()) {\n'
        '            try { var inDoc = this.input.next(); }\n'
        '            catch (err) {\n'
        '                var errDoc = new LinkedHashMap();\n'
        '                errDoc.put("error", err);\n'
        '                this.error.write(errDoc);\n'
        '            }\n'
        '        }\n'
        '    },\n'
        '    cleanup: function() {}\n'
        '};\n'
        'var hook = new com.snaplogic.scripting.language.ScriptHook(impl);\n'
    ),
    execution_mode="Execute only",
)

# ── Union ──────────────────────────────────────────────────────────────────
snap_union = FlowUnion(label="Union", execution_mode="Execute only")

# ── Masking (Delta) ────────────────────────────────────────────────────────
snap_masking_delta = TransformMapper(
    label="Masking Data Delta",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $id : lib.cdc_config.maskData($id)',
                target_path="$id",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $name : lib.cdc_config.maskData($name)',
                target_path="$name",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $status : lib.cdc_config.maskData($status)',
                target_path="$status",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $category : lib.cdc_config.maskData($category)',
                target_path="$category",
            ),
            # Repeat for each field that needs masking
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_TIMESTAMP", target_path="$CDC_TIMESTAMP"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_OPERATION", target_path="$CDC_OPERATION"
            ),
        ],
    ),
    execution_mode="Execute only",
)

# ── Delta S3 Output ────────────────────────────────────────────────────────
snap_json_fmt_delta = TransformJSONFormatter(
    label="NDJSON Format Delta",
    json_lines=True,
    pretty_print=False,
    ignore_empty_stream=True,
    execution_mode="Execute only",
)

snap_s3_delta = S3Upload(
    label="Delta S3 Upload",
    bucket="lib.cdc_config.Account.Details.Bucket.get(lib.cdc_config.getEnv())",
    object_key=(
        "lib.cdc_config.Account.Details.DELTA_S3.Object_Key"
        "+lib.cdc_config.Account.Details.DELTA_S3.Prefix_Date"
        "+lib.cdc_config.Account.Details.DELTA_S3.File_Name"
    ),
    pm_account=Expr('lib.my_shared_accounts.S3_Account.get(lib.my_shared_accounts.getEnv())'),
    execution_mode="Execute only",
)

# ── Full Mode: Masking ─────────────────────────────────────────────────────
snap_masking_full = TransformMapper(
    label="Masking Data Full",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $id : lib.cdc_config.maskData($id)',
                target_path="$id",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $name : lib.cdc_config.maskData($name)',
                target_path="$name",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $status : lib.cdc_config.maskData($status)',
                target_path="$status",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='lib.cdc_config.Obfuscation_IND.get(lib.cdc_config.getEnv()) == "N" ? $category : lib.cdc_config.maskData($category)',
                target_path="$category",
            ),
            # Repeat for each field that needs masking
            TransformMapper.Transformations.MappingTableItem(
                expression=(
                    "pipe.startTime.toLocaleDateTimeString("
                    "{'timeZone':'UTC',\"format\":\"yyyy-MM-dd'T'HH:mm:ss'.000000Z'\"})"
                ),
                target_path="$CDC_TIMESTAMP",
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression='"INSERT"',
                target_path="$CDC_OPERATION",
            ),
        ],
    ),
    execution_mode="Execute only",
)

# ── Full Mode: FlowCopy → S3 + FTP ────────────────────────────────────────
snap_full_copy = FlowCopy(label="S3 and FTP Copy", execution_mode="Execute only")

snap_json_fmt_full = TransformJSONFormatter(
    label="NDJSON Format Full",
    json_lines=True,
    pretty_print=False,
    ignore_empty_stream=True,
    execution_mode="Execute only",
)

snap_s3_full = S3Upload(
    label="Full S3 Upload",
    bucket="lib.cdc_config.Account.Details.Bucket.get(lib.cdc_config.getEnv())",
    object_key=(
        "lib.cdc_config.Account.Details.FULL_S3.Object_Key"
        "+lib.cdc_config.Account.Details.FULL_S3.Prefix_Date"
        "+lib.cdc_config.Account.Details.FULL_S3.File_Name"
    ),
    pm_account=Expr('lib.my_shared_accounts.S3_Account.get(lib.my_shared_accounts.getEnv())'),
    execution_mode="Execute only",
)

snap_remove_cdc_cols = TransformMapper(
    label="Remove CDC Columns",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_TIMESTAMP", target_path=None
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression="$CDC_OPERATION", target_path=None
            ),
        ],
    ),
    execution_mode="Execute only",
)

snap_csv_fmt = TransformCSVFormatter(
    label="Full CSV Formatter",
    delimiter="~|",
    write_header=False,
    quote_mode="ALL",
    quote_character=None,
    newline_character="LF",
    escape_char="\\",
    execution_mode="Execute only",
)

snap_ftp_writer = BinaryFileWriter(
    label="Full Data FTP",
    filename="lib.cdc_config.Account.Details.FTP.File_Name",
    file_action="OVERWRITE",
    execution_mode="Execute only",
)

# ── Delta FlowCopy (splits for TransformDiff + FTP merge) ─────────────────
snap_delta_copy = FlowCopy(label="Copy Delta", execution_mode="Execute only")

# ══════════════════════════════════════════════════════════════════════════
# CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════

# ── Prior Snapshot Loading ─────────────────────────────────────────────────
p.connect(src=snap_dir_browser, dst=snap_file_reader,
          src_view_id="out", dst_view_id="input103",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_file_reader, dst=snap_csv_parser,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_csv_parser, dst=snap_check_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_check_delta, dst=snap_sort_prior,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_sort_prior, dst=snap_diff,
          src_view_id="output0", dst_view_id="inputOriginal",
          src_output_type="document", dst_input_type="document")

# ── Source → Router ────────────────────────────────────────────────────────
p.connect(src=snap_source, dst=snap_lowercase,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_lowercase, dst=snap_router,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# ── Delta Path ─────────────────────────────────────────────────────────────
p.connect(src=snap_router, dst=snap_delta_copy,
          src_view_id="output1", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_delta_copy, dst=snap_diff,
          src_view_id="output1", dst_view_id="inputNew",
          src_output_type="document", dst_input_type="document")

# TransformDiff → Label mappers
p.connect(src=snap_diff, dst=snap_label_delete,
          src_view_id="outputDeletions", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_label_insert,
          src_view_id="outputInsertions", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_label_update,
          src_view_id="outputModified", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_diff, dst=snap_consume,
          src_view_id="outputUnmodified", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Label mappers → Union
p.connect(src=snap_label_delete, dst=snap_union,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_insert, dst=snap_union,
          src_view_id="output0", dst_view_id="input1",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_label_update, dst=snap_union,
          src_view_id="output0", dst_view_id="input101",
          src_output_type="document", dst_input_type="document")

# Union → Masking → S3 (Delta)
p.connect(src=snap_union, dst=snap_masking_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_masking_delta, dst=snap_json_fmt_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_json_fmt_delta, dst=snap_s3_delta,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")

# ── Full Path ──────────────────────────────────────────────────────────────
p.connect(src=snap_router, dst=snap_masking_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_masking_full, dst=snap_full_copy,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Full → S3
p.connect(src=snap_full_copy, dst=snap_json_fmt_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_json_fmt_full, dst=snap_s3_full,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")

# Full → FTP (remove CDC cols → CSV → FileWriter)
p.connect(src=snap_full_copy, dst=snap_remove_cdc_cols,
          src_view_id="output1", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_remove_cdc_cols, dst=snap_csv_fmt,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_csv_fmt, dst=snap_ftp_writer,
          src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
```

---

## Pattern 2: Hash-Based CDC (Alternative)

**Use when TransformDiff is not suitable** — for example, when you need custom change logic (e.g., ignoring certain fields), or when you cannot store a prior snapshot file but can persist a small hash state JSON.

> **Limitation:** Hash-based CDC does **not** natively detect DELETE operations. It only classifies records as INSERT, UPDATE, or UNCHANGED.

### When to Use Hash-Based Instead

- You need to exclude specific fields from change detection (e.g., timestamps)
- You need custom change logic beyond field-by-field comparison
- Your source data format makes TransformDiff impractical
- You want change detection without storing a full prior snapshot

### Architecture

```
[Source] → [Transform] → [Add CDC Hash] → [Sort by ID] → [FlowCopy]
                                                              |
                         [Hash Save Branch] <-----------------+
                         GroupByN → Build Hash Map → JSONFormatter → FileWriter
                                                              |
                         [Join Branch] <----------------------+
                         Left Outer Join ← FileReader → JSONParser → Expand → Sort
                                |
                         [Compute Change Type]
                                |
                         [FlowRouter] → delta_output / full_output
                                |
                         [Format] → [Write]
```

### Expression Library Functions

```javascript
{
    stringify_for_hash: (value) => (
        value == null ? ''
        : Array.isArray(value) ? JSON.stringify(value)
        : value.toString()
    ),

    compute_record_hash: (rec) => (
        Crypto.sha256([
            rec.id || '',
            (rec.name == null ? '' : (Array.isArray(rec.name) ? JSON.stringify(rec.name) : rec.name.toString())),
            rec.status || '',
            rec.category || ''
        ].join('|')).hex()
    )
}
```

> **WARNING:** `this.stringify_for_hash()` returns null in `slpy exec` — inline the stringify logic into each function. Use `lib.<name>.fn()` for cross-references (see SKILL.md Gotcha 9).

### Pipeline Parameters

```python
p.param_table = ParamTable(param=[
    ParamTable.ParamItem(capture=True, key='cdc_mode', value='full', data_type='string'),
    ParamTable.ParamItem(capture=True, key='hash_state_path', value='/tmp/hashes.json', data_type='string'),
    ParamTable.ParamItem(capture=True, key='delta_output_path', value='/tmp/delta.ndjson', data_type='string'),
    ParamTable.ParamItem(capture=True, key='full_output_path', value='/tmp/full.ndjson', data_type='string'),
])
```

### Key Snap Configurations

#### Add CDC Hash

```python
snap_add_hash = TransformMapper(
    label="Add CDC Hash",
    null_safe_access=True,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("$id"),
                target_path="$._record_id"
            ),
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("lib.helpers.compute_record_hash($)"),
                target_path="$._record_hash"
            ),
        ]
    ),
)
```

#### Left Outer Join (Current vs Previous Hashes)

```python
snap_join = TransformJoin(
    label="Join with Previous Hashes",
    join_type='Left outer',
    sorted_streams='Ascending',
    join_paths=[
        TransformJoin.JoinPathsItem(
            left_path=Expr("$_record_id"),
            right_input_view='input1',
            right_path=Expr("$_record_id")
        )
    ],
    null_safe_access=True,
)
```

#### Compute Change Type

```python
snap_change_type = TransformMapper(
    label="Compute Change Type",
    null_safe_access=True,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr(
                    "$right == null ? 'INSERT' : "
                    "($_record_hash != $right._prev_hash ? 'UPDATE' : 'UNCHANGED')"
                ),
                target_path="$._change_type"
            ),
        ]
    ),
)
```

#### Route by CDC Mode

```python
snap_router = FlowRouter(
    label="Route by CDC Mode",
    first_match=True,
    routes=[
        FlowRouter.RoutesItem(
            expression=Expr("_cdc_mode == 'delta' && $_change_type != 'UNCHANGED'"),
            output_view_name="delta_output"
        ),
        FlowRouter.RoutesItem(
            expression=Expr("_cdc_mode == 'full'"),
            output_view_name="full_output"
        ),
    ],
)
```

### First Run Handling

On first run, the hash state file doesn't exist. Use an empty state generator as fallback:

```python
snap_empty_state = TransformJSONGenerator(
    label="Generate Empty Hash State",
    editable_content='{"hashes": {}}',
)
# Connect to the expand step — provides fallback when FileReader produces no output
p.connect(src=snap_empty_state, dst=snap_expand_hashes, ...)
```

**First run behavior:**
1. FileReader attempts to load hash state file — file doesn't exist, no output
2. Empty state generator produces `{"hashes": {}}`
3. Left outer join finds no matches — all records classified as INSERT
4. Hash state saved for next run

### Hash Save Branch

```python
# Collect all records, build {id: hash} map, save as JSON
snap_collect = TransformGroupByN(label="Collect Hashes", target_field="records", group_size=0)

snap_build_map = TransformMapper(
    label="Build Hash Map",
    null_safe_access=True,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr(
                    "$records.reduce((acc, r) => acc.extend({[r._record_id]: r._record_hash}), {})"
                ),
                target_path="$.hashes"
            ),
        ]
    ),
)

snap_format_state = TransformJSONFormatter(label="Format Hash State", json_lines=False, pretty_print=True)
snap_save_state = BinaryFileWriter(label="Save Hash State", filename=Expr("_hash_state_path"), file_action='OVERWRITE')
```

### Previous State Loading

```python
snap_load_prev = BinaryFileReader(label="Load Previous Hashes", file_path=Expr("_hash_state_path"))
snap_parse_prev = TransformJSONParser(label="Parse Hash JSON", json_lines=False)

snap_expand = TransformMapper(
    label="Expand Hash Records",
    null_safe_access=True,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr(
                    "Object.keys($hashes || {}).map(id => ({_record_id: id, _prev_hash: $hashes[id]}))"
                ),
                target_path="$.records"
            ),
        ]
    ),
)

snap_split = TransformMapper(
    label="Split Hash Records",
    null_safe_access=True,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("$records"), target_path="$"
            ),
        ]
    ),
)

snap_sort_prev = TransformSort(
    label="Sort Previous Hashes",
    sort_paths=[TransformSort.SortPathsItem(sort_path="$_record_id", sort_order_ind="ascending")],
    null_safe_access=True,
)
```

### Connections

```python
# Main flow: Source → Add Hash → Sort → Branch
p.connect(src=snap_source, dst=snap_add_hash, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_add_hash, dst=snap_sort, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_sort, dst=snap_branch, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Hash save branch: FlowCopy output1 → Collect → Build Map → Format → Write
p.connect(src=snap_branch, dst=snap_collect, src_view_id="output1", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_collect, dst=snap_build_map, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_build_map, dst=snap_format_state, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_format_state, dst=snap_save_state, src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")

# Previous state: FileReader → Parse → Expand → Split → Sort
p.connect(src=snap_load_prev, dst=snap_parse_prev, src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_parse_prev, dst=snap_expand, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_expand, dst=snap_split, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_split, dst=snap_sort_prev, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# First run fallback
p.connect(src=snap_empty_state, dst=snap_expand, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Join: FlowCopy output0 + sorted prev hashes
p.connect(src=snap_branch, dst=snap_join, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_sort_prev, dst=snap_join, src_view_id="output0", dst_view_id="input1",
          src_output_type="document", dst_input_type="document")

# Change detection → Router → Output
p.connect(src=snap_join, dst=snap_change_type, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_change_type, dst=snap_router, src_view_id="output0", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")

# Output branches
p.connect(src=snap_router, dst=snap_fmt_delta, src_view_id="delta_output", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_fmt_delta, dst=snap_write_delta, src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_router, dst=snap_fmt_full, src_view_id="full_output", dst_view_id="input0",
          src_output_type="document", dst_input_type="document")
p.connect(src=snap_fmt_full, dst=snap_write_full, src_view_id="output0", dst_view_id="input0",
          src_output_type="binary", dst_input_type="binary")
```

---

## Testing CDC Pipelines

### TransformDiff-Specific Testing

#### Verify All Four Output Views

1. Run in delta mode with known changes between prior snapshot and current data
2. Confirm `outputDeletions` contains records removed since last run
3. Confirm `outputInsertions` contains new records
4. Confirm `outputModified` contains records with changed field values
5. Confirm `outputUnmodified` contains unchanged records (consumed by Script snap)

#### Test Empty Prior Snapshot (First Run)

1. Remove or ensure no prior snapshot file exists
2. Run in delta mode with `DirectoryBrowser.ignore_empty_result=True`
3. Verify all current records appear as Insertions (no prior data → no Deletions, Modified, or Unmodified)

#### Test All Records Unchanged

1. Run full mode to create prior snapshot
2. Run delta mode immediately with same source data
3. Verify: no Deletions, no Insertions, no Modified — all records go to Unmodified (consumed/discarded)
4. Verify delta S3 output is empty or contains zero records

#### Verify CDC Labels

1. Check that `CDC_OPERATION` is correctly set to `DELETE`, `INSERT`, or `UPDATE` on each output record
2. Check that `CDC_TIMESTAMP` is populated with a valid timestamp

### Hash-Based Testing

#### First Run Verification

1. Delete hash state file (if exists)
2. Run with `_cdc_mode=full`
3. Verify all records have `_change_type='INSERT'` and hash state file is created

#### Delta Run Verification

1. Run first time with `_cdc_mode=full` to establish baseline
2. Modify source data (change a field value)
3. Run with `_cdc_mode=delta`
4. Verify modified records have `_change_type='UPDATE'`, new records have `_change_type='INSERT'`, unchanged records not in delta output

#### Hash Consistency

1. Run pipeline twice with identical source data
2. Compare hash values — should be identical
3. Test edge cases: null values, empty arrays, special characters, Unicode

---

## Anti-Patterns to Avoid

### TransformDiff Anti-Patterns

#### 1. Unsorted Inputs

**Wrong:**
```python
# Connecting unsorted data directly to TransformDiff
p.connect(src=snap_source, dst=snap_diff,
          src_view_id="output0", dst_view_id="inputNew", ...)
```

**Correct:**
```python
# Sort BOTH input streams by the same key before TransformDiff
snap_sort = TransformSort(
    sort_paths=[TransformSort.SortPathsItem(sort_path="$id", sort_order_ind="global")],
    sort_order="ascending",
)
p.connect(src=snap_sort, dst=snap_diff,
          src_view_id="output0", dst_view_id="inputNew", ...)
```

TransformDiff requires both `inputOriginal` and `inputNew` to be sorted by the same key in the same order. Unsorted inputs produce incorrect diff results silently.

#### 2. Not Consuming Unmodified Output

**Wrong:**
```python
# Only connecting Deletions, Insertions, Modified — leaving Unmodified unconnected
p.connect(src=snap_diff, dst=snap_label_delete, src_view_id="outputDeletions", ...)
p.connect(src=snap_diff, dst=snap_label_insert, src_view_id="outputInsertions", ...)
p.connect(src=snap_diff, dst=snap_label_update, src_view_id="outputModified", ...)
# Missing: outputUnmodified connection → PIPELINE HANGS
```

**Correct:**
```python
# Always connect and consume outputUnmodified
p.connect(src=snap_diff, dst=snap_consume,
          src_view_id="outputUnmodified", dst_view_id="input0", ...)
```

Unconsumed output views cause the TransformDiff snap to block waiting for the downstream to read, hanging the entire pipeline.

#### 3. Swapped inputOriginal and inputNew

**Wrong:**
```python
# Current data → inputOriginal, prior data → inputNew (SWAPPED)
p.connect(src=snap_current, dst=snap_diff, dst_view_id="inputOriginal", ...)
p.connect(src=snap_prior, dst=snap_diff, dst_view_id="inputNew", ...)
```

**Correct:**
```python
# Prior data → inputOriginal, current data → inputNew
p.connect(src=snap_prior, dst=snap_diff, dst_view_id="inputOriginal", ...)
p.connect(src=snap_current, dst=snap_diff, dst_view_id="inputNew", ...)
```

Swapping produces inverted results: INSERTs appear as DELETEs and vice versa.

#### 4. Not Updating Prior Snapshot After Delta Run

The prior snapshot file (FTP/file system) must be updated after each full run so that the next delta run has an accurate baseline. Ensure the full mode path writes the snapshot file that the delta mode reads.

### Hash-Based Anti-Patterns

#### 1. Including Timestamps in Hash

**Wrong:**
```javascript
compute_record_hash: (rec) => (
    Crypto.sha256([rec.id, rec.name, rec.created_at, rec.updated_at].join('|')).hex()
)
```

**Correct:**
```javascript
compute_record_hash: (rec) => (
    Crypto.sha256([rec.id || '', rec.name || ''].join('|')).hex()
)
```

Timestamps change every run, causing false UPDATE detection on every record.

#### 2. Using Inner Join Instead of Left Outer

**Wrong:** `join_type='Inner'` — drops new records (INSERT detection fails).

**Correct:** `join_type='Left outer'` — new records have null right side, correctly classified as INSERT.

#### 3. Unsorted Streams for Join

**Wrong:** `sorted_streams='None'` — loads all data into memory, may cause OOM.

**Correct:** `sorted_streams='Ascending'` — efficient merge join using sorted streams.

#### 4. Missing First Run Handling

Always include an empty state generator (`{"hashes": {}}`) connected to the expand step as fallback when the hash state file doesn't exist yet.

#### 5. Forgetting to Save Hash State

Always include the hash save branch (FlowCopy → GroupByN → Build Map → JSONFormatter → FileWriter). Without it, every run treats all records as INSERT.

---

## Summary

| Pattern | Best For | DELETE Detection | Complexity |
|---------|----------|-----------------|------------|
| **TransformDiff** (Recommended) | Most CDC scenarios | Yes | Low |
| **Hash-Based** (Alternative) | Custom change logic, no snapshot storage | No | Medium |

**TransformDiff** is the recommended default. It uses SnapLogic's native diff capability, detects all change types including DELETEs, and requires fewer pipeline snaps. Use the hash-based approach only when you have a specific reason that TransformDiff doesn't address.
