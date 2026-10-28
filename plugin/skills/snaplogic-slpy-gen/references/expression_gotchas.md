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
| `Math.log()`, `Math.exp()`, `Math.sin()` and other log/exp/trig functions; `isFinite()`, `Number.isInteger()`, `encodeURI()`, `decodeURI()` | Not supported — the platform `Math` has only `abs ceil floor max min pow random randomUUID round sign sqrt trunc` and constants | `Math.log($x)` | Compute upstream (e.g. a Script snap); `encodeURIComponent()` for URIs; `parseFloat(x) % 1 == 0` for an integer check |

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

### Gotcha 4: Date Formatting -- toString(format) is silently ignored by the platform

`Date.now().toString(format)` looks like it works: slpy-elang honors the Java-style pattern, so
`slpy exec` returns the formatted string. The platform's `toString` implementation takes no
format argument -- it ignores whatever is passed and always returns the default ISO string. This
validates clean locally and only shows up once deployed.

```javascript
// WRONG -- the format argument is silently discarded on the platform
Date.now().toString("yyyy-MM-dd")

// CORRECT -- toLocaleDateTimeString actually reads the format
Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"})
Date.now().toLocaleDateTimeString({"format": "yyyyMMddHHmmss"})
Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"})
```

Use `toLocaleDateTimeString` for every date format, including date-only and time-only output.
`toLocaleDateString` and `toLocaleTimeString` disagree with the platform in every form: slpy-elang
returns `MM/dd/yyyy` and `hh:mm:ss AM` where the platform returns ISO, it ignores an object literal
where the platform reads it, and it accepts a bare format string that the platform rejects outright.
None of that is caught locally.

```javascript
// Anything these two can do, toLocaleDateTimeString does with a format
Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"})   // date only
Date.now().toLocaleDateTimeString({"format": "HH:mm:ss"})     // time only
Date.now().toLocaleDateTimeString({"timeZone": "America/New_York", "format": "yyyy-MM-dd"})
```

`Date.parse(dateStr, format)` supports Java-style format patterns. UTC suffix normalization is handled automatically.

**Note:** There is no `Crypto` global. Use `Math.randomUUID()` for a UUID and `Digest.sha256(str)` for a hash (it already returns hex). A UUID is random, so do not assert its exact value in tests.

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

