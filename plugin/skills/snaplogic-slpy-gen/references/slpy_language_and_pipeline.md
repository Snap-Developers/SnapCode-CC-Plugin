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

