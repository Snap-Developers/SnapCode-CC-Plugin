## 8. Expression Language Reference

The SnapLogic Expression Language is a powerful utility that allows you to use expressions (JavaScript syntax) to access functions and properties, set field values dynamically, and manipulate data within pipelines.

### Key Features

- **JavaScript-Based Syntax**: The expression language follows JavaScript syntax conventions
- **Dynamic Field Values**: Set field values dynamically based on input data
- **Data Manipulation**: Transform, filter, and process data inline
- **Function Callbacks**: Functions can be passed to other functions that accept callbacks (like `Array.map()` or `Array.filter()`)
- **Expression Libraries**: Create reusable expressions that can be imported into any pipeline

### Supported Operators

**Comparison Operators:**
- `>` (greater than)
- `>=` (greater than or equal)
- `<` (less than)
- `<=` (less than or equal)
- `==` (equals)
- `!=` (not equals)

> **Note:** Strict equals (`===`) and strict not equals (`!==`) are NOT supported.

> **There is no `new` operator.** `SnapExpressions.g4` declares a `New` token that no parser rule
> consumes, so `new Date(...)`, `new RegExp(...)`, `new Object()`, `new Array()` are **compile
> errors on the platform** — in every expression context, not just expression libraries. Use:
>
> | Instead of | Write |
> |---|---|
> | `new Date()` | `Date.now()` |
> | `new Date(str)` / `new Date(ms)` | `Date.parse(str)` / `Date.parse(ms)` |
> | `new Date(y, m, d)` | `Date.UTC(y, m, d)` |
> | `new RegExp("pat")` | `/pat/` |
> | `new Object()` / `new Array()` | `{}` / `[]` |
> | `new Set($arr)` for uniqueness | `$arr.filter((v, i, a) => a.indexOf(v) == i)` |
>
> This does NOT apply inside Script Snap bodies, which run real JavaScript/Jython where `new` is valid.

**Logical Operators:**
- `&&` (AND)
- `||` (OR)
- `!` (NOT)

---

### Using Expressions

Expressions are available across multiple Snaps. If a Snap exposes expression functionality for a property, an icon (=) appears in front of the text box of the property. Only Snap properties in the Settings category can currently provide expression functionality.

#### Accessing Document Values

To access values in a document, you can use JavaScript object accessors:

```javascript
// Using dot notation
$first_name

// Underscore-prefixed fields: dot notation is supported and preferred
$._table
$.obj._field

// Using bracket notation (required for field names with spaces, dots, or hyphens)
$['field with spaces']
$['field-name']
$['field.name']

// Nested access
$customer.address.city

// Array access
$items[0].name
```

#### Expression Toggle

Any field preceded with an equal sign (=) button can handle an expression if that button is toggled on.

**Example Expression:**
```javascript
'/out' + Date.now() + '.json'
```
This would insert the current date as part of the filename.

#### Dynamic Validation

As you create expressions, they are validated in real-time for:
- Syntax errors
- Spelling errors
- Output previews

#### Using eval()

If you need to parameterize your pipeline with an expression, you can use the `eval()` function to evaluate an expression stored in a string:

```javascript
// Substitute Pipeline parameters
$.eval(_parameter)

// Execute functions
$.eval(Date.now())
```

The `$.eval()` function can be used without having to use an expression toggle (=).

#### Pipeline Parameters

Parameters are string values that allow a pipeline to be reused in multiple situations.

```javascript
// Prefix the parameter name with an underscore
_firstName
_lastName
_filePath
```

**Important Notes:**
- The value of a parameter is always a string
- You need to convert strings to numeric values before mathematical operations
- Simply adding two to a parameter will append the character "2"

**Converting String Parameters to Numbers:**
```javascript
// Wrong - will yield "122" instead of 14
_numValue + 2

// Correct - use parseInt or parseFloat
parseInt(_numValue) + 2
parseFloat(_numValue) + 2.5
```

#### Input Fields

Input view schema attributes can be used as part of expressions using the dollar sign (`$`) prefix:

```javascript
// Access fields from input document
$customer_id
$order_total
$['Home address']  // For fields with spaces or special characters
```

---

### JSONPath

JSONPath expressions let you specify the parts of a JSON document that are to be operated on by a Snap.

#### Basic Syntax

```javascript
// Reference the "name" field at the root
$.name

// Access nested objects
$.customer.address.city

// Array access
$.items[0]

// Wildcard - all items in array
$.items[*]
```

#### Path Expressions

| Expression | Description |
|------------|-------------|
| `$` | Root object/element |
| `@` | Current object/element |
| `.` or `[]` | Child operator |
| `..` | Recursive descent |
| `*` | Wildcard (all objects/elements) |
| `[]` | Subscript operator |
| `[,]` | Union operator |
| `[start:end:step]` | Array slice operator |
| `?()` | Filter expression |
| `()` | Script expression |

#### Recursive Descent (`$..`) and Filter Expressions

The recursive descent operator (`$..`) and filter expressions (`[?(expr)]`) are supported:

```javascript
// Recursive descent - find all 'name' fields at any depth
$..name

// Recursive descent with filter
$..[?(@.status == 'active')]

// Filter objects based on value
$.addresses[?(value.type == 'home')]

// Filter by numeric comparison
$.items[?(@.price > 100)]

// Filter by existence
$.items[?(@.discount)]
```

#### Extended JSONPath Methods

SnapLogic extends standard JSONPath syntax with method calls to manipulate query results:

```javascript
// Extract first element from filtered array
$.addresses[?(value.type == 'home')].first()

// Get array length (JSONPath syntax — in expressions, use .length without parentheses)
$.items.length()

// Map over results
$.items.map(item => item.name)
```

#### Mapping Root

The **Mapping Root** property in the Mapper Snap is a JSONPath that limits the scope of a mapping:

```javascript
// Iterate over objects in an array
$.my_array[*]
```

This enables the Mapper to iterate over the objects in the array and transform each object based on the mapping.

> **Important:** Expression language syntax and JSONPath syntax are not compatible. Simple syntax like `$.name` is valid in both, but anything non-trivial will likely not work.

---

### Global Functions and Properties

Global functions are available throughout the expression language without requiring a prefix.

#### Type Checking Functions

| Function | Description | Example |
|----------|-------------|---------|
| `typeof(value)` | Returns the type of value | `typeof($field)` -> `"string"` |
| `isNaN(value)` | Checks if value is NaN | `isNaN($amount)` |

#### Parsing Functions

| Function | Description | Example |
|----------|-------------|---------|
| `parseInt(string, radix)` | Parse string to integer | `parseInt("42")` -> `42` |
| `parseFloat(string)` | Parse string to float | `parseFloat("3.14")` -> `3.14` |

#### URI Encoding Functions

| Function | Description | Example |
|----------|-------------|---------|
| `encodeURIComponent(str)` | Encodes a URI component | `encodeURIComponent("hello world")` |
| `decodeURIComponent(str)` | Decodes a URI component | `decodeURIComponent("hello%20world")` |

#### Other Global Functions

| Function | Description | Example |
|----------|-------------|---------|
| `eval(expression)` | Evaluates an expression string | `$.eval(_parameter)` |

---

### String Functions and Properties

String literals function similarly to JavaScript strings. A string literal can be constructed with either single quotes or double quotes.

**Note:** Template literals (backticks) are NOT supported in SnapLogic Expression Language. Use string concatenation with the `+` operator or `.concat()` method instead.

**Escape sequences in strings:** `\"`, `\'`, `\\`, `\n`, `\t`, `\xNN`, and `\uXXXX` all work in `.expr` files. For embedding quotes in `Expr("...")` inside Python pipeline files, use alternating quote styles (`Expr("field == 'value'")`), `\uXXXX` escapes (`\u0022` for `"`), or move complex string construction to an `.expr` library function.

#### String Properties

| Property | Description | Example |
|----------|-------------|---------|
| `.length` | Returns string length | `"hello".length` -> `5` |

#### String Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.charAt(index)` | Character at index | `"hello".charAt(0)` -> `"h"` |
| `.charCodeAt(index)` | Unicode value at index | `"A".charCodeAt(0)` -> `65` |
| `.concat(str1, str2, ...)` | Concatenate strings | `"Hello".concat(" ", "World")` |
| `.indexOf(searchValue)` | First index of value | `"hello".indexOf("l")` -> `2` |
| `.lastIndexOf(searchValue)` | Last index of value | `"hello".lastIndexOf("l")` -> `3` |
| `.localeCompare(str)` | Compare strings | `"a".localeCompare("b")` -> `-1` |
| `.match(regexp)` | Match against regex | `"test123".match(/\d+/)` |
| `.replace(search, replace)` | Replace occurrences | `"hello".replace("l", "L")` |
| `.search(regexp)` | Search for pattern | `"hello".search(/l/)` -> `2` |
| `.slice(start, end)` | Extract substring | `"hello".slice(1, 4)` -> `"ell"` |
| `.split(separator)` | Split into array | `"a,b,c".split(",")` -> `["a","b","c"]` |
| `.substring(start, end)` | Extract substring | `"hello".substring(1, 4)` -> `"ell"` |
| `.toLowerCase()` | Convert to lowercase | `"HELLO".toLowerCase()` -> `"hello"` |
| `.toUpperCase()` | Convert to uppercase | `"hello".toUpperCase()` -> `"HELLO"` |
| `.trim()` | Remove whitespace | `"  hello  ".trim()` -> `"hello"` |
| `.trimLeft()` | Trim leading whitespace | `"  hello".trimLeft()` |
| `.trimRight()` | Trim trailing whitespace | `"hello  ".trimRight()` |
| `.startsWith(searchStr)` | Check if starts with | `"hello".startsWith("he")` -> `true` |
| `.endsWith(searchStr)` | Check if ends with | `"hello".endsWith("lo")` -> `true` |
| `.contains(searchStr)` | Check if contains | `"hello".contains("ll")` -> `true` |
| `.sprintf(format, args...)` | Format string (printf-style) | `"%s has %d items".sprintf(name, count)` |
| `.lowerFirst()` | Lowercase first char | `"Hello".lowerFirst()` -> `"hello"` |
| `.upperFirst()` | Uppercase first char | `"hello".upperFirst()` -> `"Hello"` |
| `.camelCase()` | Convert to camelCase | `"foo_bar".camelCase()` -> `"fooBar"` |
| `.snakeCase()` | Convert to snake_case | `"fooBar".snakeCase()` -> `"foo_bar"` |
| `.kebabCase()` | Convert to kebab-case | `"fooBar".kebabCase()` -> `"foo-bar"` |
| `.repeat(count)` | Repeat string | `"ab".repeat(3)` -> `"ababab"` |
| `String.fromCharCode(code)` | Character from Unicode code point | `String.fromCharCode(34)` -> `"\""` |

---

### Number Functions and Properties

Number functions work similarly to JavaScript Number object methods.

| Method | Description | Example |
|--------|-------------|---------|
| `.toFixed(digits)` | Format with fixed decimals | `(3.14159).toFixed(2)` -> `"3.14"` |
| `.toExponential(digits)` | Format in exponential notation | `(12345).toExponential(2)` -> `"1.23e+4"` |
| `.toPrecision(precision)` | Format to precision | `(3.14159).toPrecision(3)` -> `"3.14"` |
| `.toString(radix)` | Convert to string | `(255).toString(16)` -> `"ff"` |

```javascript
// Fixed decimal places
$price.toFixed(2)  // "19.99"

// Scientific notation
$largeNumber.toExponential(3)  // "1.234e+6"

// Significant figures
$measurement.toPrecision(4)  // "12.34"
```

---

### Math Functions and Properties

Math functions provide mathematical operations and constants.

> **Note:** Not all supported methods may appear in the Functions and Properties drop-down list. If not available, you may type them in.

#### Math Constants

| Constant | Description | Value |
|----------|-------------|-------|
| `Math.E` | Euler's number | ~2.718 |
| `Math.LN2` | Natural log of 2 | ~0.693 |
| `Math.LN10` | Natural log of 10 | ~2.303 |
| `Math.LOG2E` | Base 2 log of E | ~1.443 |
| `Math.LOG10E` | Base 10 log of E | ~0.434 |
| `Math.PI` | Pi | ~3.14159 |
| `Math.SQRT1_2` | Square root of 1/2 | ~0.707 |
| `Math.SQRT2` | Square root of 2 | ~1.414 |

#### Basic Math Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.abs(x)` | Absolute value | `Math.abs(-5)` -> `5` |
| `Math.ceil(x)` | Round up | `Math.ceil(4.2)` -> `5` |
| `Math.floor(x)` | Round down | `Math.floor(4.8)` -> `4` |
| `Math.round(x)` | Round to nearest | `Math.round(4.5)` -> `5` |
| `Math.trunc(x)` | Truncate to integer | `Math.trunc(4.9)` -> `4` |
| `Math.sign(x)` | Sign of number | `Math.sign(-5)` -> `-1` |

#### Min/Max Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.max(a, b, ...)` | Maximum value | `Math.max(1, 5, 3)` -> `5` |
| `Math.min(a, b, ...)` | Minimum value | `Math.min(1, 5, 3)` -> `1` |

#### Power and Root Functions

| Function | Description | Example |
|----------|-------------|---------|
| `Math.pow(base, exp)` | Power | `Math.pow(2, 3)` -> `8` |
| `Math.sqrt(x)` | Square root | `Math.sqrt(16)` -> `4` |

#### Random Number

| Function | Description | Example |
|----------|-------------|---------|
| `Math.random()` | Random number 0-1 | `Math.random()` -> `0.7234...` |

**Generate random integer in range:**
```javascript
// Random integer from 0 to max (exclusive)
Math.floor(Math.random() * max)

// Random integer from min to max (inclusive)
Math.floor(Math.random() * (max - min + 1)) + min
```

---

### Date Functions and Properties

Dates function similarly to JavaScript Date objects. A Date represents the number of milliseconds since midnight January 1, 1970 UTC.

**Important Notes:**
- Timestamp formats may differ across different databases or APIs
- Migrating date information may have unintended results if differences are not considered
- Time zone settings between Cloudplex and Groundplex might differ (Cloudplex may be in UTC, while Groundplex could be in local time zone)

#### Creating Dates

```javascript
// Current date/time
Date.now()

// From timestamp (milliseconds)
// CAUTION: the epoch path is gated behind the DATE_PARSE_TS_UTC feature flag
// (Date.java:543, default false), so the DateTime is built in the node's default
// zone, not UTC -- Cloudplex and Groundplex can differ. Pass an ISO string, or
// format explicitly with toLocaleDateTimeString({"timeZone": "UTC"}), when it matters.
Date.parse(1609459200000)

// From string
Date.parse("2021-01-01")
Date.parse("2021-01-01T12:00:00Z")

// From components (year, month, day, hour, minute, second, ms)
// Note: month is 0-indexed (0 = January)
Date.UTC(2021, 0, 1, 12, 0, 0, 0)
```

#### Date Comparison

Dates can be compared using relational operators:
```javascript
date1 > date2
date1 >= date2
date1 < date2
date1 <= date2
date1 == date2
```

#### Date Get Methods (Local Time)

| Method | Description | Example |
|--------|-------------|---------|
| `.getFullYear()` | Get year (4 digits) | `date.getFullYear()` -> `2021` |
| `.getMonth()` | Get month (1-12) | `date.getMonth()` -> `1` (January) |
| `.getMonthFromZero()` | Get month (0-11, JS convention) | `date.getMonthFromZero()` -> `0` (January) |
| `.getDate()` | Get day of month (1-31) | `date.getDate()` -> `15` |
| `.getDay()` | Get day of week (0-6) | `date.getDay()` -> `0` (Sunday) |
| `.getHours()` | Get hours (0-23) | `date.getHours()` -> `14` |
| `.getMinutes()` | Get minutes (0-59) | `date.getMinutes()` -> `30` |
| `.getSeconds()` | Get seconds (0-59) | `date.getSeconds()` -> `45` |
| `.getMilliseconds()` | Get milliseconds (0-999) | `date.getMilliseconds()` |
| `.getTime()` | Get timestamp (ms since epoch) | `date.getTime()` |
| `.getTimezoneOffset()` | Get timezone offset (minutes) | `date.getTimezoneOffset()` |

// Note: getMonth() is 1-indexed (1 = January); getMonthFromZero() is 0-indexed

#### Date Get Methods (UTC)

| Method | Description |
|--------|-------------|
| `.getUTCFullYear()` | Get UTC year |
| `.getUTCMonth()` | Get UTC month (1-12) |
| `.getUTCMonthFromZero()` | Get UTC month (0-11, JS convention) |
| `.getUTCDate()` | Get UTC day of month |
| `.getUTCDay()` | Get UTC day of week |
| `.getUTCHours()` | Get UTC hours |
| `.getUTCMinutes()` | Get UTC minutes |
| `.getUTCSeconds()` | Get UTC seconds |
| `.getUTCMilliseconds()` | Get UTC milliseconds |

#### Date Arithmetic Methods (Joda extensions — all return NEW Date)

Dates are **immutable**. These methods return a new Date; they do not modify the original.

| Method | Description | Example |
|--------|-------------|---------|
| `.plusDays(n)` | Add days | `date.plusDays(1)` |
| `.plusMonths(n)` | Add months | `date.plusMonths(3)` |
| `.plusYears(n)` | Add years | `date.plusYears(1)` |
| `.plusHours(n)` | Add hours | `date.plusHours(12)` |
| `.plusMinutes(n)` | Add minutes | `date.plusMinutes(30)` |
| `.plusSeconds(n)` | Add seconds | `date.plusSeconds(60)` |
| `.plusMillis(n)` | Add milliseconds | `date.plusMillis(500)` |
| `.plusWeeks(n)` | Add weeks | `date.plusWeeks(2)` |
| `.plus(ms)` | Add milliseconds (generic) | `date.plus(5000)` |
| `.minusDays(n)` | Subtract days | `date.minusDays(7)` |
| `.minusMonths(n)` | Subtract months | `date.minusMonths(1)` |
| `.minusYears(n)` | Subtract years | `date.minusYears(1)` |
| `.minusHours(n)` | Subtract hours | `date.minusHours(6)` |
| `.minusMinutes(n)` | Subtract minutes | `date.minusMinutes(15)` |
| `.minusSeconds(n)` | Subtract seconds | `date.minusSeconds(30)` |
| `.minusMillis(n)` | Subtract milliseconds | `date.minusMillis(100)` |
| `.minusWeeks(n)` | Subtract weeks | `date.minusWeeks(1)` |
| `.minus(ms)` | Subtract milliseconds (generic) | `date.minus(5000)` |

#### Date Field Replacement Methods (Joda extensions — all return NEW Date)

| Method | Description | Example |
|--------|-------------|---------|
| `.withYear(n)` | Set year | `date.withYear(2025)` |
| `.withMonthOfYear(n)` | Set month (1-12) | `date.withMonthOfYear(6)` |
| `.withDayOfMonth(n)` | Set day of month | `date.withDayOfMonth(1)` |
| `.withDayOfWeek(n)` | Set day of week (1=Mon, 7=Sun) | `date.withDayOfWeek(1)` |
| `.withDayOfYear(n)` | Set day of year | `date.withDayOfYear(1)` |
| `.withHourOfDay(n)` | Set hour | `date.withHourOfDay(9)` |
| `.withMinuteOfHour(n)` | Set minute | `date.withMinuteOfHour(0)` |
| `.withSecondOfMinute(n)` | Set second | `date.withSecondOfMinute(0)` |
| `.withMillisOfSecond(n)` | Set millisecond | `date.withMillisOfSecond(0)` |

#### Date Formatting Methods

| Method | Platform output | Note |
|--------|-----------------|------|
| `.toLocaleDateTimeString({"format": "..."})` | as the format says | **use this one for every format** |
| `.toString()` | `"2021-01-01T00:00:00.000Z"` | ISO, takes no argument |
| `.toLocaleDateTimeString()` | `"2011-10-06T15:01:12.123"` | ISO local date-time, not a locale string |
| `.toLocaleDateString()` | `"2011-10-06"` | ISO date. Avoid: see below |
| `.toLocaleTimeString()` | `"15:01:12.123"` | ISO time. Avoid: see below |

The no-argument outputs above are the platform's, taken from `DateClassMethodTest`. slpy-elang
returns locale-style strings there instead (`10/06/2011`, `03:01:12 PM`), so `slpy exec` will not
match. Pass a `format` and both agree.

**Avoid `toLocaleDateString` and `toLocaleTimeString` entirely.** They diverge from the platform in
every form: on the no-argument output above, on an object literal (slpy-elang ignores it and returns
`MM/dd/yyyy`), and on a bare format string like `toLocaleDateString("MMMM")`, which slpy-elang
accepts and the platform rejects at runtime. `toLocaleDateTimeString({"format": "..."})` covers
date-only and time-only output and agrees on both engines.

**Methods that do NOT exist** (common JS assumptions that fail in Tectonic):
`toISOString()`, `toDateString()`, `toTimeString()`, `toUTCString()`, `valueOf()`.
Use `.toString()` for ISO output. `.toString(format)` is NOT a real method: the platform
ignores any argument and always returns the ISO form, silently diverging from slpy-elang, which
does honor it. Use `.toLocaleDateTimeString({"format": "..."})` for custom formats instead.

#### Date Parsing

```javascript
// Parse date string
Date.parse("2021-01-01T12:00:00Z")  // Returns timestamp
```

The `toLocaleDateString()`, `toLocaleDateTimeString()`, and `toLocaleTimeString()` methods work with database types that are output as Joda DateTime objects.

---

### Array Functions and Properties

Array literals function similarly to JavaScript array literals.

> **Note:** Extra commas in array literals are NOT supported.

#### Creating Arrays

```javascript
// Array literal
[1, 2, 3]

// Mixed types
[1, "two", true, null]

// Nested arrays
[[1, 2], [3, 4]]

// Empty array
[]
```

#### Array Properties

| Property | Description | Example |
|----------|-------------|---------|
| `.length` | Number of elements | `[1, 2, 3].length` -> `3` |

#### Array Access Methods

| Method | Description | Example |
|--------|-------------|---------|
| `[index]` | Access by index | `arr[0]` |
| `.indexOf(item)` | Find first index | `[1,2,3].indexOf(2)` -> `1` |
| `.lastIndexOf(item)` | Find last index | `[1,2,1].lastIndexOf(1)` -> `2` |
| `.find(fn)` | Find first matching | `arr.find(x => x > 2)` |
| `.findIndex(fn)` | Find index of first matching | `arr.findIndex(x => x > 2)` |

#### Array Transformation Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.map(fn)` | Transform each element | `[1,2,3].map(x => x * 2)` -> `[2,4,6]` |
| `.filter(fn)` | Filter elements | `[1,2,3].filter(x => x > 1)` -> `[2,3]` |
| `.reduce(fn, init)` | Reduce to single value | `[1,2,3].reduce((a,b) => a+b, 0)` -> `6` |
| `.reduceRight(fn, init)` | Reduce from right | `[1,2,3].reduceRight((a,b) => a+b, 0)` |

#### Array Modification Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.concat(arr2)` | Concatenate arrays | `[1,2].concat([3,4])` -> `[1,2,3,4]` |
| `.slice(start, end)` | Extract portion | `[1,2,3,4].slice(1,3)` -> `[2,3]` |
| `.splice(start, count, items...)` | Add/remove elements | `arr.splice(1, 2, 'a', 'b')` |
| `.push(item)` | Add to end | `arr.push(4)` |
| `.pop()` | Remove from end | `arr.pop()` |
| `.shift()` | Remove from start | `arr.shift()` |
| `.unshift(item)` | Add to start | `arr.unshift(0)` |
| `.reverse()` | Reverse in place | `[1,2,3].reverse()` -> `[3,2,1]` |
| `.sort(fn)` | Sort in place | `[3,1,2].sort()` -> `[1,2,3]` |


#### Array Joining

| Method | Description | Example |
|--------|-------------|---------|
| `.join(separator)` | Join to string | `[1,2,3].join('-')` -> `"1-2-3"` |
| `.toString()` | Convert to string | `[1,2,3].toString()` -> `"1,2,3"` |

---

### Object Functions and Properties

Object literals allow you to construct an object with a set of properties.

#### Creating Objects

```javascript
// Object literal
{ name: "John", age: 30 }

// Nested objects
{
  person: { name: "John" },
  items: [1, 2, 3]
}

// Computed property names
{ [dynamicKey]: value }
```

#### Object Static Methods

| Method | Description | Example |
|--------|-------------|---------|
| `Object.keys(obj)` | Get array of keys | `Object.keys({a:1, b:2})` -> `["a","b"]` |
| `Object.values(obj)` | Get array of values | `Object.values({a:1, b:2})` -> `[1,2]` |
| `Object.entries(obj)` | Get array of [key, value] | `Object.entries({a:1})` -> `[["a",1]]` |

#### Object Instance Methods

| Method | Description | Example |
|--------|-------------|---------|
| `.hasOwnProperty(key)` | Check if has property | `obj.hasOwnProperty("name")` |
| `.hasPath(key)` | Check path exists with non-null value | `obj.hasPath("address.city")` |
| `.isEmpty()` | Check if no properties | `{}.isEmpty()` -> `true` |
| `.extend(obj1, obj2, ...)` | Merge objects into copy (non-mutating) | `$obj.extend({"status": "active"})` |
| `.get(key, default?)` | Get value with optional default | `$obj.get("email", "unknown")` |
| `.getFirst(key, default?)` | Get first element if value is list | `$obj.getFirst("tags", "none")` |
| `.merge(other)` | Merge another object | `$obj.merge($overlay)` |
| `.filter(fn)` | Filter entries by predicate (v, k, obj) | `$obj.filter((v, k) => v != null)` |
| `.mapKeys(fn)` | Transform keys (v, k, obj) | `$obj.mapKeys((v, k) => k.toUpperCase())` |
| `.mapValues(fn)` | Transform values (v, k, obj) | `$obj.mapValues(v => v * 2)` |
| `.toString()` | Convert to string | `$obj.toString()` |

#### Spread Operator

A JSON Array of objects with unique/non-overlapping keys can be converted to an object using the extend object method along with a Spread Operator:

```javascript
// Merge objects
{ ...$obj1, ...$obj2 }

// Merge using extend
{}.extend($obj1, $obj2)
```

#### Converting Array to Object

```javascript
// Using spread to merge array of objects
{ ...$array[0], ...$array[1], ...$array[2] }

// Using extend with list of [key, value] pairs
{}.extend([["a", 1], ["b", 2], ["c", 3]])
// Result: {a: 1, b: 2, c: 3}
```

---

### JSON Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `JSON.parse(string)` | Parse JSON string to object | `JSON.parse('{"a":1}')` -> `{a: 1}` |
| `JSON.stringify(obj)` | Convert object to JSON string | `JSON.stringify({a: 1})` -> `'{"a":1}'` |
| `JSON.stringify(obj, null, indent)` | Pretty print with indentation | `JSON.stringify(obj, null, 2)` |

```javascript
// Parse JSON string
let data = JSON.parse($jsonString)

// Stringify with formatting
JSON.stringify($object, null, 2)

// Access parsed data
JSON.parse($jsonField).propertyName
```

---

### Base64 Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `Base64.encode(string)` | Encode string to Base64 | `Base64.encode("Hello")` -> `"SGVsbG8="` |
| `Base64.decode(string)` | Decode Base64 to string | `Base64.decode("SGVsbG8=")` -> `"Hello"` |
| `Base64.encodeAsBinary(data)` | Encode to Base64 as bytes | `Base64.encodeAsBinary(byteArray)` |
| `Base64.decodeAsBinary(string)` | Decode Base64 to bytes | `Base64.decodeAsBinary("SGVsbG8=")` |
| `Base64.decodeGZip(string)` | Decode Base64 and decompress gzip | `Base64.decodeGZip(encoded)` |
| `Base64.decodeGZipAsBinary(string)` | Decode Base64 and decompress to bytes | `Base64.decodeGZipAsBinary(encoded)` |

Use Cases: encoding binary data for transmission, encoding credentials for Basic Authentication, encoding file contents.

---

### Digest Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `Digest.md5(string)` | MD5 hash | `Digest.md5("alpha")` -> `"2c1743a391305fbf367df8e4f069f9f9"` |
| `Digest.sha1(string)` | SHA-1 hash | `Digest.sha1("alpha")` |
| `Digest.sha256(string)` | SHA-256 hash | `Digest.sha256("alpha")` |
| `Digest.sha512(string)` | SHA-512 hash | `Digest.sha512("alpha")` |

Use Cases: creating checksums, password hashing (use SHA-256 or better for security), data integrity verification.

---

### GZip Functions and Properties

| Method | Description | Example |
|--------|-------------|---------|
| `GZip.compress(data)` | Compress data | `GZip.compress("Hello World")` |
| `GZip.decompress(data)` | Decompress data | `GZip.decompress(compressedData)` |

Use Cases: reducing payload size for API calls, compressing large text data, working with compressed file formats.

> For Base64+GZip patterns, use: `Base64.encode(GZip.compress(data))` to compress and encode, `Base64.decodeGZip(encoded)` to decode and decompress.

---

### iconv - Encode and Decode Functions

Supported encoding types: UTF-8, UTF-16, UTF-32.

| Method | Description | Example |
|--------|-------------|---------|
| `iconv.encode(string, encoding)` | Encode to specified encoding | `iconv.encode("Hello", "UTF-16")` |
| `iconv.decode(bytes, encoding)` | Decode from specified encoding | `iconv.decode(data, "UTF-8")` |

---

### HTML - Encode and Decode Functions

| Method | Description | Example |
|--------|-------------|---------|
| `HTML.encode(string)` | Encode to HTML entities | `HTML.encode("<div>")` -> `"&lt;div&gt;"` |
| `HTML.decode(string)` | Decode HTML entities | `HTML.decode("&lt;div&gt;")` -> `"<div>"` |

**Common HTML Entities:**

| Character | Entity |
|-----------|--------|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `&` | `&amp;` |
| `"` | `&quot;` |
| `'` | `&#39;` |

---

### Pipeline Functions and Properties

| Property | Description | Example |
|----------|-------------|---------|
| `pipe.label` | Pipeline label/name | `pipe.label` -> `"My Pipeline"` |
| `pipe.ruuid` | Runtime UUID | `pipe.ruuid` -> `"abc123..."` |
| `pipe.args` | Map of pipeline parameters | `pipe.args['paramName']` |
| `pipe.plexPath` | Snaplex path | `pipe.plexPath` |
| `pipe.projectPath` | Project path | `pipe.projectPath` |

#### Accessing Pipeline Parameters

```javascript
// Direct parameter access
_parameterName

// Through pipe.args
pipe.args['parameterName']
pipe.args.parameterName
```

#### Generating Unique IDs

Use `pipe.ruuid` to generate unique identifiers for pipeline runs:

```javascript
// Create unique filename
"output_" + pipe.ruuid + ".json"
```

---

### Snap Functions and Properties

| Property | Description | Example |
|----------|-------------|---------|
| `snap.label` | Snap label | `snap.label` -> `"Mapper (Data)"` |
| `snap.instanceId` | Snap instance ID | `snap.instanceId` |

```javascript
// Include snap label in error messages
"Error in " + snap.label + ": " + $errorMessage

// Create snap-specific identifiers
snap.label + "_" + Date.now()
```

---

### Task Properties and Functions

| Property | Description | Example |
|----------|-------------|---------|
| `task.label` | Task label | `task.label` -> `"My Triggered Task"` |
| `task.ruuid` | Task Runtime UUID | `task.ruuid` |

When working with enterprise schedulers, you can use `pipe.ruuid` in a Mapper Snap to return the Runtime ID when the Triggered Task runs:

```javascript
// In Mapper expression
{
  "ruuid": pipe.ruuid
}
```

---

### SL Functions and Properties

SL (SnapLogic) functions provide SnapLogic-specific utilities.

| Function | Description | Example |
|----------|-------------|---------|
| `sl.ensureArray(value)` | Ensure value is array | `sl.ensureArray([1,2,3])` -> `[1,2,3]` |
| `sl.ensureArray(value)` | Wrap non-array in array | `sl.ensureArray("x")` -> `["x"]` |
| `sl.gethostbyname(hostname)` | Get IP address | `sl.gethostbyname("www.snaplogic.com")` |
| `sl.range(start, end, step)` | Generate number range | `sl.range(0, 5, 1)` -> `[0,1,2,3,4]` |
| `sl.zip(arr1, arr2)` | Zip arrays together | `sl.zip([1,2], ["a","b"])` -> `[[1,"a"],[2,"b"]]` |
| `sl.zipObject(keys, values)` | Create object from arrays | `sl.zipObject(["a","b"], [1,2])` -> `{a:1, b:2}` |

#### sl.ensureArray Examples

```javascript
// Already an array - returns as-is
sl.ensureArray([1, 2, 3])  // [1, 2, 3]

// Single value - wraps in array
sl.ensureArray("single")   // ["single"]

// Null/undefined handling
sl.ensureArray(null)       // [null] or []
```

#### sl.range Examples

```javascript
// Generate sequence
sl.range(1, 6, 1)   // [1, 2, 3, 4, 5]
sl.range(0, 10, 2)  // [0, 2, 4, 6, 8]
```

---

### The match Control Operator

The `match` operator allows you to choose an expression to be executed based on whether an input value matches a given pattern. It is useful when you need to execute different expressions based on complex conditions.

#### Syntax

```javascript
match (inputValue) {
  pattern1 => expression1,
  pattern2 => expression2,
  _ => defaultExpression
}
```

#### Examples

```javascript
// Match on string values
match ($status) {
  "active" => "Account is active",
  "pending" => "Account is pending approval",
  "suspended" => "Account has been suspended",
  _ => "Unknown status"
}

// Match with conditions
match ($score) {
  x if x >= 90 => "A",
  x if x >= 80 => "B",
  x if x >= 70 => "C",
  x if x >= 60 => "D",
  _ => "F"
}
```

Use Cases: status code translation, category assignment, conditional transformations, switch-case style logic.

---

### Expression Language Examples

#### Conditional Expressions

```javascript
// Ternary operator
$age >= 18 ? "Adult" : "Minor"

// Nested ternary (each else-branch parenthesized — see Gotcha 1)
$score >= 90 ? "A" : ($score >= 80 ? "B" : ($score >= 70 ? "C" : "D"))

// Null coalescing
$value || "default"
$name != null ? $name : "Unknown"
```

#### String Examples

**Checking for Non-empty String:**
```javascript
$field != null && $field.length > 0
$field != null && $field.trim() != ""
```

**Checking for Existing Value:**
```javascript
$field != null
typeof($field) != "undefined"
```

**Creating Email from Name:**
```javascript
$firstName.charAt(0).toLowerCase() + $lastName.toLowerCase() + "@company.com"
```

#### Date Examples

**Creating and Formatting a Date in Specific Timezone:**
```javascript
Date.parse("2026-08-25T02:00:00.000Z").toLocaleDateTimeString({"format": "yyyy-MM-dd", "timeZone": "America/New_York"})
// "2026-08-24" — shifted back a day by the timezone
```

Use `toLocaleDateTimeString`, **not** `toLocaleDateString`. slpy-elang's `toLocaleDateString`
never reads the `timeZone` key, so the shift silently does not happen during local validation and
the output diverges from the platform.

**Formatting Date with Letters:**
```javascript
Date.now().toLocaleDateTimeString({"format": "MMMM d, yyyy"})
// "January 15, 2021"
```

> **Pass the options as an object literal.** `toLocaleDateTimeString` reads it on both engines, and
> the platform lints the JSON-string form as slower (`DateMethod`'s own resolution text says to use
> an object literal). Recognised keys: `format`, `timeZone`, `locale`.
>
> The JSON-string form is only required by `toLocaleDateString` and `toLocaleTimeString`, which is
> one of several reasons not to use those two at all.

**Creating ISO-formatted Date:**
```javascript
Date.now().toString()
// "2021-01-15T12:00:00.000Z"
```

**Parsing a Date:**
```javascript
Date.parse($dateString)
Date.parse("2021-01-15")
```

**Parsing Non-standard Date:**
```javascript
// For "15/01/2021" format (DD/MM/YYYY)
let parts = $dateString.split("/");
Date.UTC(parts[2], parts[1] - 1, parts[0])
```

**Current Month Name:**
```javascript
Date.now().toLocaleDateTimeString({"format": "MMMM"})
// "January"
```

#### Filtering Examples

**Filtering for Two Possible Values:**
```javascript
$items.filter(item => item.status == "active" || item.status == "pending")
```

**Filtering by Multiple Fields:**
```javascript
$items.filter(item => item.category == "A" && item.price > 100)
```

**Filtering by Date within Timeframe:**
```javascript
let now = Date.now();
let oneWeekAgo = now - (7 * 24 * 60 * 60 * 1000);
$items.filter(item => Date.parse(item.date) >= oneWeekAgo)
```

#### Object Manipulation Examples

**Merging Objects:**
```javascript
{}.extend($obj1, $obj2)
{ ...$obj1, ...$obj2 }
```

**Extracting Specific Fields:**
```javascript
{
  id: $source.id,
  name: $source.name,
  email: $source.contact.email
}
```

**Creating Object from Arrays:**
```javascript
sl.zipObject($keys, $values)
```

#### Array Transformation Examples

**Mapping to Extract Field:**
```javascript
$users.map(user => user.email)
```

**Calculating Sum:**
```javascript
$numbers.reduce((sum, n) => sum + n, 0)
```

**Finding Maximum:**
```javascript
$numbers.reduce((max, n) => n > max ? n : max, $numbers[0])
Math.max(...$numbers)
```

**Grouping by Property:**
```javascript
$items.reduce((groups, item) => {
  let key = item.category;
  groups[key] = groups[key] || [];
  groups[key].push(item);
  return groups;
}, {})
```

---

### Quick Reference Tables

#### Common Patterns

| Task | Expression |
|------|------------|
| Check if null | `$field != null` |
| Default value | `$field \|\| "default"` |
| String to number | `parseInt($field)` or `parseFloat($field)` |
| Number to string | `$field.toString()` |
| Current timestamp | `Date.now()` |
| Current date (ISO) | `Date.now().toString()` |
| Array length | `$array.length` |
| First element | `$array[0]` |
| Last element | `$array[$array.length - 1]` |
| Unique values | `$array.filter((v, i, arr) => arr.indexOf(v) == i)` |
| Sort ascending | `$array.sort((a,b) => a - b)` |
| Sort descending | `$array.sort((a,b) => b - a)` |

#### Useful Conversions

| From | To | Expression |
|------|----|------------|
| String | Integer | `parseInt($str)` |
| String | Float | `parseFloat($str)` |
| Number | String | `$num.toString()` |
| Array | String | `$arr.join(",")` |
| String | Array | `$str.split(",")` |
| Object | JSON String | `JSON.stringify($obj)` |
| JSON String | Object | `JSON.parse($str)` |
| Date | Timestamp | `$date.getTime()` |
| Timestamp | Date | `Date.parse($timestamp)` |

---

