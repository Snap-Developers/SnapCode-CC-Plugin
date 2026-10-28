## 10. Generation Templates

### Complete Pipeline Structure Template

```python
"""
Pipeline Name: {Descriptive Pipeline Name}

Pipeline Summary:
{2-3 sentence description of what this pipeline does, data sources,
transformations, and destinations}

{Optional Script Snap Warning if applicable - see Checkpoint 3}

Snap Inventory:
(#snap_0) {SnapName}: {Brief description of snap purpose and key configuration}
(#snap_1) {SnapName}: {Brief description of snap purpose and key configuration}
(#snap_2) {SnapName}: {Brief description of snap purpose and key configuration}
...

Data Flow:
{Source} -> {Parse/Transform steps} -> {Destination}

Error Handling:
{Description of error routing and handling strategy}

Configuration Parameters:
- {param_name}: {description and default value}
...

Execution Validation:
- Fully executable: {Yes/No}
- Test segment needed: {Yes/No}
"""

# Standard imports for SLPy
from slpy.modules.Pipeline.Pipeline import Pipeline
from slpy.modules.Pipeline.utils.open_view import OPEN_VIEW
from slpy.modules.Pipeline.utils import Expr
from slpy.modules.Pipeline.param_table.ParamTable import ParamTable
# Expression library import (if .expr file is generated)
from slpy.modules.Pipeline.expression_libraries.ExpressionLibraries import ExpressionLibraries

# Snap imports (import only snaps used in this pipeline)
from slpy.modules.Snap.BinaryFileReader import BinaryFileReader
from slpy.modules.Snap.TransformCSVParser import TransformCSVParser
from slpy.modules.Snap.TransformMapper import TransformMapper
from slpy.modules.Snap.TransformJSONFormatter import TransformJSONFormatter
from slpy.modules.Snap.BinaryFileWriter import BinaryFileWriter
from slpy.modules.Snap.FlowFilter import FlowFilter
from slpy.modules.Snap.FlowRouter import FlowRouter

# Pipeline initialization
p = Pipeline(label='{Descriptive Pipeline Name}')

# Pipeline parameters (if needed)
# All parameters are strings by default - cast in expressions if needed
p.param_table = ParamTable(param=[
    ParamTable.ParamItem(
        capture=True,  # Capture parameter value at runtime
        key='input_file_path',  # Parameter name (access as _input_file_path)
        value='input.csv',  # Default value (always string)
        data_type='string'  # Data type (string, number, boolean)
    ),
    ParamTable.ParamItem(
        capture=True,
        key='batch_size',
        value='1000',  # Default as string
        data_type='number'
    ),
    ParamTable.ParamItem(
        capture=True,
        key='debug_mode',
        value='false',  # Boolean as string
        data_type='boolean'
    )
])

# Expression library configuration (REQUIRED when .expr file is generated)
# This imports the expression library so functions can be called via lib.{alias}.*
p.expression_libraries = ExpressionLibraries(expression_library=[
    ExpressionLibraries.ExpressionLibraryItem(
        path='{name}_helpers.expr',  # Path to the generated .expr file
        as_='helpers'                 # Alias for use in expressions (lib.helpers.*)
    )
])

# Snap instantiation with detailed configuration
# Every snap carries a label naming the step it performs: two words of <= 12 characters
# (a third word usually clips on the canvas), unique within the pipeline -- Rule 12

# READ phase - Binary file input
snap_0 = BinaryFileReader(
    label="Read CSV",
    file_path=Expr("_input_file_path"),  # Use parameter (Expr required for _)
    # Additional configuration as needed
)

# PARSE phase - Convert binary to documents
snap_1 = TransformCSVParser(
    label="Parse CSV",
    contains_header=True,
    delimiter=',',
    quote_character='"',
    # Additional configuration as needed
)

# TRANSFORM phase - Data transformations
snap_2 = TransformMapper(
    label="Map Customers",
    transformations=TransformMapper.Transformations(
        mapping_table=[
            # Map output fields from input document ($)
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$id"), target_path="$.customer_id"),  # Direct field copy
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$first_name + ' ' + $last_name"), target_path="$.full_name"),  # Concatenation
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$email.toLowerCase()"), target_path="$.email"),  # Method chaining
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$order_amount * 1.08"), target_path="$.order_total"),  # Arithmetic
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$order_count > 10"), target_path="$.is_vip"),  # Boolean expression
            TransformMapper.Transformations.MappingTableItem(expression=Expr("Date.now()"), target_path="$.created_date"),  # Built-in function
            # Expression library reference (REQUIRED when .expr file generated)
            # Use lib.helpers.* to call functions from {name}_helpers.expr
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.helpers.calculate_discount($tier, $amount)"), target_path="$.discount"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.helpers.format_phone($phone)"), target_path="$.formatted_phone"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.helpers.categorize_score($score)"), target_path="$.category"),
        ]
    ),
)

# Optional: Filtering
snap_3 = FlowFilter(
    label="Filter Active",
    filter_expression=Expr("$status == 'active' && $order_total > 0")  # Expr for $
)

# Optional: Routing
snap_4 = FlowRouter(
    label="Route by Region",
    routes=[
        FlowRouter.RoutesItem(
            expression=Expr("$region == 'US'"),
            output_view_name="us"
        ),
        FlowRouter.RoutesItem(
            expression=Expr("$region == 'EU'"),
            output_view_name="eu"
        )
    ]
)

# FORMAT phase - Convert documents to binary
snap_5 = TransformJSONFormatter(
    label="Format as JSON",
    pretty_print=True  # Human-readable JSON
)

# WRITE phase - Binary file output
snap_6 = BinaryFileWriter(
    label="Write JSON",
    filename="output.json"  # Plain string (no Expr needed)
)

# Connections - Define data flow between snaps
# Always specify type compatibility

# READ -> PARSE (binary -> binary)
p.connect(
    src=snap_0,
    dst=snap_1,
    src_view_id="output0",  # Output view of source snap
    dst_view_id="input0",   # Input view of destination snap
    src_output_type="binary",  # Source outputs binary
    dst_input_type="binary"    # Destination expects binary
)

# PARSE -> TRANSFORM (document -> document)
p.connect(
    src=snap_1,
    dst=snap_2,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",  # Parser outputs documents
    dst_input_type="document"    # Mapper expects documents
)

# TRANSFORM -> FILTER (document -> document)
p.connect(
    src=snap_2,
    dst=snap_3,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document"
)

# FILTER -> FORMAT (document -> document)
p.connect(
    src=snap_3,
    dst=snap_5,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document"
)

# FORMAT -> WRITE (binary -> binary)
p.connect(
    src=snap_5,
    dst=snap_6,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="binary",  # Formatter outputs binary
    dst_input_type="binary"    # Writer expects binary
)

# Fan-out connections - every branch carries a src_view_label, or the canvas shows
# a bare "output0"/"output1". On a router the label repeats the route's
# output_view_name exactly; on a copy snap it names where the branch goes.
# p.connect(
#     src=snap_4,
#     dst=snap_us,
#     src_view_id="output0",
#     src_view_label="us",  # same string as the route's output_view_name
#     dst_view_id="input0",
#     src_output_type="document",
#     dst_input_type="document"
# )

# Error handling connections (if applicable)
# Connect error views to error pipeline or logging

# Example: Map error view to error handler
# p.connect(
#     src=snap_2,
#     dst=snap_error_handler,
#     src_view_id="error0",  # Error output view
#     dst_view_id="input0",
#     src_output_type="document",
#     dst_input_type="document"
# )
```

### Expression Library Template (.expr)

```javascript
{
    // Constants (simple values)
    tax_rate: 0.08,
    max_discount: 0.30,
    default_currency: 'USD',

    // Date/Time Helpers (single-expression functions)
    // toLocaleDateTimeString takes an object literal; it is the only date formatter
    // that agrees with the platform on every form
    get_today: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"}),
    get_today_iso: () => Date.now().toLocaleDateTimeString({"format": "yyyy-MM-dd"}),
    get_timestamp: () => Date.now().toLocaleDateTimeString({"format": "yyyyMMdd'T'HHmmss"}),
    prev_month_start: () => Date.now().minusMonths(1).withDayOfMonth(1),
    prev_month_end: () => Date.now().withDayOfMonth(1).minusDays(1),
    current_quarter_start: () => Date.now().minusMonths((Date.now().getMonth() - 1) % 3).withDayOfMonth(1),

    // Formatting Functions
    format_phone: (phone) => phone.replace(/[^0-9]/g, ''),
    format_currency: (amount) => '$' + amount.toFixed(2),
    format_full_name: (first, last) => (first + ' ' + last).trim().toUpperCase(),

    // Business Logic (ternary for conditionals)
    calculate_discount: (tier, amount) =>
        (tier == 'platinum' ? amount * 0.80 :
        (tier == 'gold' ? amount * 0.85 :
        (tier == 'silver' ? amount * 0.90 :
        (tier == 'bronze' ? amount * 0.95 :
        amount)))),

    calculate_shipping: (weight, zone) =>
        (zone == 'domestic' ?
            (weight < 5 ? 10 : (weight < 10 ? 15 : 20)) :
        (zone == 'international' ?
            (weight < 5 ? 25 : (weight < 10 ? 40 : 60)) :
        0)),

    // Categorization
    categorize_age: (age) =>
        (age < 18 ? 'minor' :
        (age < 65 ? 'adult' :
        'senior')),

    categorize_score: (score) =>
        (score >= 90 ? 'A' :
        (score >= 80 ? 'B' :
        (score >= 70 ? 'C' :
        (score >= 60 ? 'D' :
        'F')))),

    // Validation (return boolean)
    is_valid_email: (email) => email.contains('@') && email.contains('.'),
    is_valid_zip: (zip) => zip.match(/^\d{5}(-\d{4})?$/) != null,
    is_weekend: (date) => date.getDay() == 0 || date.getDay() == 6,

    // Array Operations (use .map, .filter, .reduce - no loops)
    sum_amounts: (items) => items.map(i => i.amount).reduce((a, b) => a + b, 0),
    filter_active: (users) => users.filter(u => u.status == 'active'),
    extract_ids: (records) => records.map(r => r.id),

    // String Operations
    truncate: (str, len) => str.length > len ? str.substring(0, len) + '...' : str,
    capitalize: (str) => str.charAt(0).toUpperCase() + str.slice(1).toLowerCase(),
    remove_spaces: (str) => str.replace(/\s+/g, ''),

    // Conditional Logic (nested ternary)
    get_priority: (amount, customer_tier) =>
        (customer_tier == 'platinum' ? 'high' :
        (customer_tier == 'gold' ? (amount > 1000 ? 'high' : 'medium') :
        (customer_tier == 'silver' ? 'medium' :
        (amount > 500 ? 'medium' : 'low')))),

    // NEVER use this.otherFunction() (returns null in slpy exec) — use lib.<name>.fn() or inline
    calculate_total_with_tax: (amount) => amount + (amount * 0.08),
    calculate_tax: (amount) => amount * 0.08,

    // Complex calculations (inline all dependencies)
    calculate_net_price: (gross, discount_tier) =>
        (discount_tier == 'gold' ? gross * 0.8 : (discount_tier == 'silver' ? gross * 0.9 : gross))
        + ((discount_tier == 'gold' ? gross * 0.8 : (discount_tier == 'silver' ? gross * 0.9 : gross)) * 0.08),

    // Data Transformation (use individual target_path mappings in TransformMapper, not object literals)
    format_full_name: (first, last) => first + ' ' + last,
    categorize_age: (age) => (age >= 65 ? 'senior' : (age >= 18 ? 'adult' : 'minor'))
}
```

**Using Expression Library in Pipeline:**

```python
# In pipeline docstring, document expression library usage
"""
Expression Library: customer_helpers.expr
Functions used:
- lib.calculate_discount(tier, amount): Apply tier-based discount
- lib.format_phone(phone): Normalize phone number format
- lib.is_valid_email(email): Validate email format
"""

# In TransformMapper, reference library functions with lib.
snap_2 = TransformMapper(
    label="Apply Discounts",
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.calculate_discount($tier, $amount)"), target_path="$.discounted_price"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.format_phone($phone)"), target_path="$.phone_normalized"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.is_valid_email($email)"), target_path="$.email_valid"),
            TransformMapper.Transformations.MappingTableItem(expression=Expr("lib.format_full_name($first, $last)"), target_path="$.full_name"),
        ]
    ),
)
```

---

