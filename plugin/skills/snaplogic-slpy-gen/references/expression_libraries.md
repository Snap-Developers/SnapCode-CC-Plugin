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
- **NO reserved word as a bare object key or parameter name** -- `instanceof`, `typeof`, `in`, `matches`, `match`, `if`, `true`, `false`, `new`, `null`, `NaN`, `Infinity`. This applies anywhere in the file, including objects built inside a function. The platform reads the word as a keyword and the import fails with `Expression parsing failed near -- >> match <<`. Quote the key instead: `"match": ...` (reading it back as `x.match` still works). Use a different parameter name: `(value) => ...`, not `(in) => ...`. `function` is fine as a key. Names that only contain a keyword (`matchPostcodeOnLine`) and method calls (`.match()`) are fine. `slpy validate-expression` reports it
- **NO `===` or `!==`** -- use `==` and `!=` instead
- **NO `new`** -- SEL has no `new` operator anywhere, not just in `.expr` files. Use `Date.now()`, `Date.parse(x)`, `Date.UTC(y, m, d)`, a `/pattern/` literal, `{}` and `[]`. See the note in `expression_language.md` for the full table. (Script Snap bodies are exempt — they are real JavaScript/Jython.)
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
- Built-in functions: `Math.*`, `Date.now().toString()`, `Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"})`, `Date.parse(str, format)`, etc.
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
  get_today: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"}),

  get_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"}),

  get_compact_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMddHHmmss"}),

  toMonthDate: (x) => x.withDayOfMonth(1),

  prevMonthStart: (x) => (x != null ? x : Date.now()).minusMonths(1).withDayOfMonth(1),

  prevMonthEnd: (x) => (x != null ? x : Date.now()).withDayOfMonth(1).minusDays(1),

  prevMonthStartString: (x) => (x != null ? x : Date.now()).minusMonths(1).withDayOfMonth(1).toLocaleDateTimeString({"format": "yyyy-MM-dd"}),

  prevMonthEndString: (x) => (x != null ? x : Date.now()).withDayOfMonth(1).minusDays(1).toLocaleDateTimeString({"format": "yyyy-MM-dd"}),

  firstDayOfMonth: (date) => date.withDayOfMonth(1),

  lastDayOfMonth: (date) => date.plusMonths(1).withDayOfMonth(1).minusDays(1),

  toEpoch: (date) => Math.floor(date.getTime() / 1000),

  fromEpoch: (seconds) => Date.parse(seconds * 1000)
}
```

**Usage in Pipeline:**
```javascript
lib.date_utils.get_today()                 // "2026-01-15"
lib.date_utils.get_timestamp()             // "20260115T143522"
lib.date_utils.prevMonthStartString()      // "2025-12-01"
lib.date_utils.toEpoch(Date.now())         // 1704067200
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

  isNumeric: (value) => value != null && !isNaN(parseFloat(value)) && parseFloat(value) != Infinity && parseFloat(value) != -Infinity,

  isInteger: (value) => value != null && !isNaN(parseFloat(value)) && parseFloat(value) != Infinity && parseFloat(value) != -Infinity && parseFloat(value) % 1 == 0,

  inRange: (value, min, max) =>
    !isNaN(parseFloat(value)) && parseFloat(value) >= min && parseFloat(value) <= max,

  hasLength: (str, min, max) =>
    ((str != null ? str : '').length >= min) && (max == null || (str != null ? str : '').length <= max),

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

  get_today: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"}),
  get_today_iso: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"}),
  get_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"}),

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
  to_csv_field: (value) => (value == null || value + "" == "null") ? "" : value + "",
  format_number: (numStr) => ('' + (parseFloat(numStr) / 1000)),

  get_api_url: (host) => "https://" + host + "/api/v1"
}
```

---

### Validation Checklist

Before generating or editing an expression library, verify every item in the **Restrictions** section above (FORBIDDEN Constructs + ALLOWED Only). Additionally check:
- [ ] **NO self-referencing in TransformMapper** -- if `$field` is a `target_path` in the same mapper AND is not in the input, split into sequential mappers (Gotcha 12)

#### Date Formatting Patterns

`.toString(format)` does not exist on the platform -- it ignores the argument and always returns
ISO. Use `.toLocaleDateTimeString({"format": "..."})`, which is also the only date formatter
that agrees with the platform on every form (see Gotcha 4).

```javascript
// yyyy-MM-dd (e.g., "2026-01-15")
get_date: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"})

// yyyyMMdd'T'HHmmss (e.g., "20260115T143522") — quoted 'T' produces literal T
get_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"})

// yyyyMMddHHmmss (e.g., "20260115143522")
get_compact_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMddHHmmss"})

// Dynamic filename with date
make_filename: (prefix) => prefix + Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"}) + ".csv"
```

`Date.parse(dateStr, format)` also supports a 2-arg signature with Java-style format patterns for parsing non-standard date strings.

#### Null-Safe Patterns

```javascript
// String coercion (NEVER use String(), Number(), Boolean() constructors)
format_value: (numStr) => ('' + (parseFloat(numStr) / 1000))

// Null-safe value access
safe_string: (value) => (value != null ? value : "")

// Null check for CSV fields (a missing argument is null too)
to_csv_field: (value) => (value == null || value + "" == "null") ? "" : value + ""

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

