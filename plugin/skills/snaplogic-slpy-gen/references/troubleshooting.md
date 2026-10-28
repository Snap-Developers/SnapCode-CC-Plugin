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
5. **Re-run validation:** `cd <pipeline_dir> && slpy translate -src file.py -dest file.slp -strict -expr`

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

### Execution Validation Errors (`slpy exec`)

**Error**: Unsupported snap type '{SnapName}'
**Cause**: The pipeline contains a snap that `slpy exec` cannot run locally (e.g., Salesforce, Snowflake, SAP snaps).
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

When passing pipeline parameters to `slpy exec`, use the `-e` flag:

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
| `Crypto.uuid()`, `Crypto.sha256()` | `Crypto is undefined` | No `Crypto` global: use `Math.randomUUID()` and `Digest.sha256()` |

**Debugging approach:** When `slpy exec` produces null where a value is expected, create a minimal debug pipeline (4-5 snaps) isolating the suspect expression. Check against the patterns above before investigating further.

### Comparison: `slpy translate` vs `slpy exec`

| Aspect | `slpy translate` | `slpy exec` |
|--------|------------------|----------------|
| **Purpose** | Syntax validation + .slp generation | Runtime validation of data flow |
| **What it catches** | Invalid snap names, type mismatches, missing Expr(), syntax errors, expression library issues | Null references, incorrect transformations, wrong output structure, logic errors, data type issues |
| **When to run** | ALWAYS (mandatory) | When feasible (recommended) |
| **Prerequisites** | Valid .py file | Successful translate + supported snaps + input data |
| **Output** | .slp file (deployment artifact) | Pipeline output files + execution log |
| **Snap support** | All snaps | Subset only (run `slpy exec --list-snaps`) |
| **Speed** | Fast (static analysis) | Slower (actual data processing) |
| **Replaces the other?** | No -- both are complementary | No -- translate is always required first |

### Target Columns Empty After a Lookup / Select / Execute

**Symptom:** The pipeline translates, imports, and runs with no error, but the target rows are empty, mostly empty, or the writer reports a missing key column. Validation was clean at every checkpoint.

**Cause:** The snap upstream of the failing Mapper re-roots the document — it emits its own output fields at the root and nests the entire input under `original` (Rule 11). Bare `$field` references resolve to null. If the Mapper uses `null_safe_access=True` with `!= null ? ... : undefined` guards, the null becomes `undefined` and the column is dropped from the write instead of raising.

**Diagnosis:** For each snap whose class name ends in `Lookup`, `Select`, or `Execute`, look at the snap directly downstream. Every field reference there that is *not* one of the upstream snap's declared `output_fields` must be prefixed `$original.`.

```python
# Symptom shape — every upstream field silently drops
"sfid": Expr("$Id != null ? $Id : undefined")

# Fix
"sfid": Expr("$original.Id != null ? $original.Id : undefined")
```

**Note:** `slpy exec` will not surface this for database lookups — they are outside the executable snap set. Catch it at Checkpoint 2 instead.
