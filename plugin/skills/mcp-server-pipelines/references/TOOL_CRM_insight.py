"""
Pipeline Name: TOOL_CRM_insight

Pipeline Summary: SnapLogic-authored reference *tool* pipeline showing the branching shape: route on
an argument, answer from data on the happy path, return a fixed message otherwise, merge with a
Union. Same tool markers as every tool (a description, an argument schema, the 'tool' tag) - the
identical contract serves an MCP server and an agent driver. The argument schema here is
'p.tool_input_parameters' (the Designer Tool tab's JSON Schema) rather than 'p.param_table'; the
tool description is the schema's 'description'. Two conventions worth copying: the
final mapper on each branch projects the answer onto '$content', and the not-found branch returns a
plain explanatory string instead of an empty stream (an empty tool result reads as a failure to the
calling LLM).

(#snap_0) FlowRouter: Routes on the 'company_name' argument (read as '$company_name' off the input document) - known companies to output0, everything else to output1.
(#snap_1) TransformJSONGenerator: Stands in for the real CRM lookup - swap for a DB/API snap in a real tool. 'pass_through_prop=True' keeps the inbound request available as '$original' downstream.
(#snap_2) FlowFilter: Keeps only the record matching the requested company ('$companyName == $original.company_name').
(#snap_3) TransformMapper: Drops the passed-through '$original' echo before shaping the result.
(#snap_4) TransformMapper: Projects the matched record onto '$content'.
(#snap_6) TransformMapper: The not-found branch - maps a fixed message onto '$content'.
(#snap_5) FlowUnion: Merges both branches into the single tool result stream.
"""

from slpy.modules.Pipeline.Pipeline import Pipeline, Tags, ToolInputParameters
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.FlowFilter import FlowFilter
from slpy.modules.Snap.FlowRouter import FlowRouter
from slpy.modules.Snap.FlowUnion import FlowUnion
from slpy.modules.Snap.TransformJSONGenerator import TransformJSONGenerator
from slpy.modules.Snap.TransformMapper import TransformMapper

p = Pipeline(
    label="TOOL_CRM_insight",
    purpose="Retrieves customer relationship data from the internal CRM system",
)

p.tags = Tags(value=["tool"])

p.tool_input_parameters = ToolInputParameters(
    value={
        "type": "object",
        "description": "Retrieves customer relationship data from the internal CRM system",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "The name of the customer company to search for in the CRM",
            },
        },
        "required": ["company_name"],
    }
)


snap_0 = FlowRouter(
    label="Router",
    routes=[
        FlowRouter.RoutesItem(
            expression=Expr('["SnapLogic", "Amazon", "Microsoft"].find(company => company == $company_name) != null'),
            output_view_name="output0",
        ),
        FlowRouter.RoutesItem(
            expression=Expr('["SnapLogic", "Amazon", "Microsoft"].find(company => company == $company_name) == null'),
            output_view_name="output1",
        ),
    ],
    first_match=False,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = TransformJSONGenerator(
    label="CRM",
    editable_content='[\n  {\n    "companyId": "SL-00123",\n    "companyName": "SnapLogic",\n    "industry": "Software & Data Integration",\n    "currentDeals": [\n      {\n        "dealId": "SL-D-2025-032",\n        "dealName": "Enterprise Integration Platform Renewal",\n        "value": 285000,\n        "probability": 80,\n        "expectedCloseDate": "2025-06-15"\n      }\n    ],\n    "accountStatus": "Active",\n    "lastInteraction": "2025-02-28",\n    "notes": "Interested in expanding their data integration solutions to include more AI capabilities."\n  },\n  {\n    "companyId": "AMZN-00456",\n    "companyName": "Amazon",\n    "industry": "E-commerce & Cloud Computing",\n    "currentDeals": [\n      {\n        "dealId": "AMZN-D-2025-087",\n        "dealName": "Warehouse Management Solution",\n        "value": 1250000,\n        "probability": 65,\n        "expectedCloseDate": "2025-05-30"\n      }\n    ],\n    "accountStatus": "Active",\n    "lastInteraction": "2025-03-01",\n    "notes": "Looking to optimize logistics operations across North American distribution centers."\n  },\n  {\n    "companyId": "MS-00789",\n    "companyName": "Microsoft",\n    "industry": "Software & Cloud Services",\n    "currentDeals": [\n      {\n        "dealId": "MS-D-2025-122",\n        "dealName": "Azure Integration Services",\n        "value": 750000,\n        "probability": 90,\n        "expectedCloseDate": "2025-04-15"\n      }\n    ],\n    "accountStatus": "Active",\n    "lastInteraction": "2025-02-15",\n    "notes": "Exploring co-development opportunities for enterprise solutions."\n  }\n]',
    array_elements_as_documents=True,
    pass_through_prop=True,
    support_type_exts=False,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_2 = FlowFilter(
    label="Filter",
    filter_expression=Expr("$companyName == $original.company_name"),
    null_safe_access=False,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_3 = TransformMapper(
    label="remove original",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_table=[TransformMapper.Transformations.MappingTableItem(expression=Expr("$original"), target_path=None)],
        mapping_root="$",
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_4 = TransformMapper(
    label="content wrapper",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[TransformMapper.Transformations.MappingTableItem(expression=Expr("$"), target_path="content")],
        mapping_root="$",
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_5 = FlowUnion(
    label="Union", preserve_order=None, sort_paths=[], execution_mode="Validate & Execute", error_behavior="fail"
)

snap_6 = TransformMapper(
    label="Mapper2",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('"The company is not found in CRM"'), target_path="content"
            )
        ],
        mapping_root="$",
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

p.connect(
    src=OPEN_VIEW.INPUT,
    dst=snap_0,
    src_view_id="OPEN_VIEW.INPUT",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_0,
    dst=snap_1,
    src_view_id="output0",
    dst_view_id="input101",
    dst_view_label="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_1,
    dst=snap_2,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_2,
    dst=snap_3,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_3,
    dst=snap_4,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_4,
    dst=snap_5,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_0,
    dst=snap_6,
    src_view_id="output1",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_6,
    dst=snap_5,
    src_view_id="output0",
    dst_view_id="input1",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_5,
    dst=OPEN_VIEW.OUTPUT,
    src_view_id="output0",
    dst_view_id="OPEN_VIEW.OUTPUT",
    src_output_type="document",
    dst_input_type="document",
)
