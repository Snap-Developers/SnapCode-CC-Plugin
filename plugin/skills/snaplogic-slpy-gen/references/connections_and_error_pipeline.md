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
- Special: `"OPEN_VIEW.OUTPUT"` (pipeline output)

**Common Patterns**:
```python
# Multiple outputs (Router, Copy) — name each branch (Rule 12)
p.connect(src=snap_router, dst=snap_high, src_view_id="output0", src_view_label="high", ...)
p.connect(src=snap_router, dst=snap_low, src_view_id="output1", src_view_label="low", ...)

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
p.connect(src=snap_1, dst=OPEN_VIEW.OUTPUT, src_view_id="output0", dst_view_id="OPEN_VIEW.OUTPUT", src_output_type="document", dst_input_type="document")
```

**Branching with Router**:
```python
# Every fan-out branch carries a src_view_label, or the canvas shows a bare
# output0/output1 (Rule 12). On a router the label is not free: it repeats the
# route's output_view_name byte for byte, because the snap emits to that name.
snap_router = FlowRouter(routes=[
    FlowRouter.RoutesItem(expression=Expr("$amount > 1000"), output_view_name="high"),
    FlowRouter.RoutesItem(expression=Expr("$amount <= 1000"), output_view_name="low"),
])
p.connect(src=snap_router, dst=snap_high, src_view_id="output0", src_view_label="high", dst_view_id="input0", ...)
p.connect(src=snap_router, dst=snap_low,  src_view_id="output1", src_view_label="low",  dst_view_id="input0", ...)
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
# A copy snap names no views of its own, so the branch labels are yours to pick.
snap_copy = FlowBinaryCopy(label='Fork Stream')
p.connect(src=snap_reader, dst=snap_copy, src_output_type="binary", dst_input_type="binary")
p.connect(src=snap_copy, dst=snap_processing, src_view_id="output0", src_view_label="Process", dst_input_type="binary", ...)
p.connect(src=snap_copy, dst=snap_archive_writer, src_view_id="output1", src_view_label="Archive", dst_input_type="binary", ...)
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

