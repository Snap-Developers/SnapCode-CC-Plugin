"""
Pipeline Name: TOOL_MongoDB_Query

Pipeline Summary: This is a minimal fixed-format MongoDB query tool pipeline. The param_table must not be modified or extended, and the snap configuration is fixed except the fields called out below. It queries a MongoDB collection and previews sample documents. The 'purpose' field in the pipeline must always be written. It should clearly describe the function of this tool so that the agent can understand what the tool does. A detailed and specific description is encouraged.

(#snap_0) MongoDBFind: This configuration is fixed-format except collection_name (required) and query_db: set collection_name from the user's request, and query_db when known. If the user did not name a collection, keep the empty string and tell the user to fill it in before running — the snap cannot execute without it.
(#snap_1) FlowGate: Aggregates the result stream into a single document. OPTIONAL - SnapLogic's own tool references omit it. Keep it when the tool would otherwise return many documents and one is wanted; remove it (and its links) otherwise. Note this fixed-format reference ships capture=True on its params — copy it verbatim; the default capture=False (as in TOOL_Search) is right for ordinary tools.
"""

from slpy.modules.Pipeline.Pipeline import ParamTable, Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.FlowGate import FlowGate
from slpy.modules.Snap.MongoDBFind import MongoDBFind

p = Pipeline(
    label="TOOL_MongoDB_Query",
    purpose="Query a MongoDB collection and return the matching documents. Accepts a find query, a projection, and a sort condition. When unsure what to pass, call it with the default values mentioned in each parameter's description first — it returns sample documents showing the collection's structure.",
)
p.tags = Tags(value=["tool"])

p.param_table = ParamTable(
    param=[
        ParamTable.ParamItem(
            key="query_condition",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="This is the MongoDB query object. If no specific condition is known, use {} as the default value.",
        ),
        ParamTable.ParamItem(
            key="projection_condition",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="This field specifies which fields to include or exclude in the MongoDB query result (similar to the projection parameter). If no specific condition is known, use {} as the default value.",
        ),
        ParamTable.ParamItem(
            key="sort_condition",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="Defines the sorting order for the query result (e.g., {'age': 1} for ascending). If no specific condition is known, use {} as the default value.",
        ),
    ]
)


snap_0 = MongoDBFind(
    label="MongoDB - Find",
    query_db="",
    collection_name="",
    query_condition=Expr("$query_condition"),
    projection_condition=Expr("$projection_condition"),
    sort_condition=Expr("$sort_condition"),
    batch_size=0,
    offset_value=None,
    limit_value=None,
    time_zone_offset=MongoDBFind.TimeZoneOffset(hours_offset=0, minutes_offset=0),
    ignore_empty_result=False,
    group_result=False,
    pass_through=True,
    retries=0,
    retry_int=1,
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
    src_view_id="output0",
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
