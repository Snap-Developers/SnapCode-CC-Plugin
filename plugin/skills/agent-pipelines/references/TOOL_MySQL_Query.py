"""
Pipeline Name: TOOL_MySQL_Query

Pipeline Summary: This is a minimal fixed-format MySQL query tool pipeline. The param_table must not be modified or extended, and the snap configuration is fixed except the fields called out below. It queries a MySQL table and previews sample rows. The 'purpose' field in the pipeline must always be written. It should clearly describe the function of this tool so that the agent can understand what the tool does. A detailed and specific description is encouraged.

(#snap_0) MySQLSelect: This configuration is fixed-format except table_name (required) and schema_name: set table_name from the user's request, and schema_name when known. If the user did not name a table, keep the empty string and tell the user to fill it in before running — the snap cannot execute without it.
(#snap_1) FlowGate: Aggregates the result stream into a single document. OPTIONAL - SnapLogic's own tool references omit it. Keep it when the tool would otherwise return many documents and one is wanted; remove it (and its links) otherwise. Note this fixed-format reference ships capture=True on its params — copy it verbatim; the default capture=False (as in TOOL_Search) is right for ordinary tools.
"""

from slpy.modules.Pipeline.Pipeline import ParamTable, Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.FlowGate import FlowGate
from slpy.modules.Snap.MySQLSelect import MySQLSelect

p = Pipeline(
    label="TOOL_MySQL_Query",
    purpose="Query a MySQL database table and return the matching rows. Accepts a SQL WHERE clause, an offset, and a row limit. When unsure what to pass, call it with the default values mentioned in each parameter's description first — it returns sample rows you can use to build a precise query.",
)
p.tags = Tags(value=["tool"])

p.param_table = ParamTable(
    param=[
        ParamTable.ParamItem(
            key="where_clause",
            value="1=1",
            capture=True,
            required=True,
            data_type="string",
            description="This field defines the SQL WHERE clause or condition used to filter results (e.g., age > 30 AND city = 'LA'). If no specific condition is known, use 1=1 as the default value.",
        ),
        ParamTable.ParamItem(
            key="limit_offset",
            value="0",
            capture=True,
            required=True,
            data_type="string",
            description="Specifies the offset position for the SQL query (e.g., 10). If no specific condition is known, use 0 as the default value.",
        ),
        ParamTable.ParamItem(
            key="limit_rows",
            value="1",
            capture=True,
            required=True,
            data_type="string",
            description="Defines the maximum number of rows to return (e.g., 20). If no specific condition is known, use 1 as the default value.",
        ),
    ]
)


snap_0 = MySQLSelect(
    label="MySQL - Select",
    schema_name="",
    table_name="",
    where_clause=Expr("$where_clause"),
    order_by=[],
    limit_offset=Expr("$limit_offset"),
    limit_rows=Expr("$limit_rows"),
    output_fields=[],
    fetch_output_fields_in_schema=False,
    pass_through=True,
    ignore_empty_result=False,
    auto_commit="False",
    match_data_types=False,
    max_retry_prop=0,
    retry_interval_prop=1,
    staging_mode="In memory",
    session_params_prop=[],
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = FlowGate(
    label="Gate",
    ignore_empty_stream=False,
    output_doc_content="All input documents",
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

p.connect(
    src=snap_0,
    dst=snap_1,
    src_view_id="outputRows",
    src_view_label="rows",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=OPEN_VIEW.INPUT,
    dst=snap_0,
    src_view_id="OPEN_VIEW.INPUT",
    dst_view_id="input101",
    dst_view_label="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_1,
    dst=OPEN_VIEW.OUTPUT,
    src_view_id="output0",
    dst_view_id="OPEN_VIEW.OUTPUT",
    src_output_type="document",
    dst_input_type="document",
)
