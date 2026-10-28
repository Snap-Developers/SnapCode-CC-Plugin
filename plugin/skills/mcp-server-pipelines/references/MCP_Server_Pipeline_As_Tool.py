"""
Pipeline Name: MCP_Server_Pipeline_As_Tool

Pipeline Summary: This is the SnapLogic-authored reference *MCP server* pipeline - the canonical
Pipeline-as-Tool shape to copy for any MCP server. It serves the two MCP protocol methods itself:
'tools/list' (the Function Generator's tool metadata flows straight through the Router's list view)
and 'tools/call' (the Router's call view dispatches to the requested tool pipeline via Pipeline
Execute). Two things make it an MCP server: 'p.tags = Tags(value=["mcp_server"])' (required for
registration as an MCP Server asset) and this exact 5-snap topology. Only the Function Generator's
'pipeline_section' entries change per server - everything else is fixed-format boilerplate.

(#snap_0) LLMUtilitiesMultiPipelineFunctionGenerator: Declares the tool list. One PipelineSectionItem per tool pipeline; 'pipeline_path' is the tool pipeline's LABEL (resolved within the same project), not a filesystem path. Its open input view is 'input101' (display label 'input0') - not a typo.
(#snap_1) MCPServerRouter: Routes list vs call. output0 ("Tool list view") answers tools/list; output1 ("Tool call view") carries tools/call requests. 'request=Expr("$original")' passes the inbound MCP request through.
(#snap_2) FlowPipelineExecute: Runs the selected tool. 'pipeline=Expr("$sl_tool_metadata.path")' is the key binding - the Router resolves the called tool's path into it per request. 'executable_during_suggest=True' keeps tool metadata discoverable at design time.
(#snap_3) FlowUnion: Merges the tools/list response (Router output0) with the tools/call result (Pipeline Execute output0).
(#snap_4) TransformMapper: Strips every top-level key starting with "original" (the Router's echo of the inbound request) so the MCP client never sees it.
"""

from slpy.modules.Pipeline.Pipeline import Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.FlowPipelineExecute import FlowPipelineExecute
from slpy.modules.Snap.FlowUnion import FlowUnion
from slpy.modules.Snap.LLMUtilitiesMultiPipelineFunctionGenerator import LLMUtilitiesMultiPipelineFunctionGenerator
from slpy.modules.Snap.MCPServerRouter import MCPServerRouter
from slpy.modules.Snap.TransformMapper import TransformMapper

p = Pipeline(label="MCP_Server_Pipeline_As_Tool")

p.tags = Tags(value=["mcp_server"])


snap_0 = LLMUtilitiesMultiPipelineFunctionGenerator(
    label="Multi Pipeline Function Generator",
    pipeline_section=[
        LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(pipeline_path="TOOL_Search", strict_mode=False),
        LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(
            pipeline_path="TOOL_CRM_insight", strict_mode=False
        ),
    ],
    aggregated_pipeline_path=Expr(None),
    aggregated_strict_mode=False,
    aggregate_input=False,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = MCPServerRouter(
    label="MCP Server Router", request=Expr("$original"), execution_mode="Validate & Execute", error_behavior="fail"
)

snap_2 = FlowPipelineExecute(
    label="Pipeline Execute",
    pipeline=Expr("$sl_tool_metadata.path"),
    snaplex_governor="SNAPLEX_WITH_PATH",
    snaplex=None,
    exec_label=Expr(None),
    params=[FlowPipelineExecute.ParamsItem(param_name=None, param_value=Expr(None))],
    reuse=False,
    batch_size=1,
    pool_size=1,
    timeout=None,
    retry_limit=None,
    retry_interval=None,
    loop_document=Expr(None),
    executable_during_suggest=True,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_3 = FlowUnion(
    label="Union", preserve_order=None, sort_paths=[], execution_mode="Validate & Execute", error_behavior="fail"
)

snap_4 = TransformMapper(
    label="Remove Original",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('$.filter((value, key) => !key.startsWith("original"))'), target_path="$"
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
    dst_view_id="input101",
    dst_view_label="input0",
    src_output_type="document",
    dst_input_type="document",
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
    src=snap_1,
    dst=snap_2,
    src_view_id="output1",
    src_view_label="Tool call view",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_1,
    dst=snap_3,
    src_view_id="output0",
    src_view_label="Tool list view",
    dst_view_id="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_2,
    dst=snap_3,
    src_view_id="output0",
    dst_view_id="input1",
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
    dst=OPEN_VIEW.OUTPUT,
    src_view_id="output0",
    dst_view_id="OPEN_VIEW.OUTPUT",
    src_output_type="document",
    dst_input_type="document",
)
