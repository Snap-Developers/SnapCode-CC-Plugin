"""
Pipeline Name: TOOL_Search

Pipeline Summary: This is the SnapLogic-authored reference *tool* pipeline - the canonical shape to
copy for any tool that calls an external API. Three things make it a tool: 'purpose' (the description
the agent reads to decide when to call it), 'p.param_table' (the agent-facing argument schema;
'p.tool_input_parameters' is the JSON Schema alternative - declare each argument in only one), and
'p.tags = Tags(value=["tool"])' (without the tag the tool is invisible to the Multi Pipeline Function
Generator picker). Params are declared with the default 'capture=False' and are read inside snaps as
expressions - '$query' here. Note there is NO FlowGate: the same tool works for an agent driver and
for an MCP server. The last snap projects the result onto '$content', which is the field convention
for handing a tool result back to the agent.

(#snap_0) APISuiteHTTPClient: Calls the external API. Parameter values reach the request through expressions - the JSON body here is Expr('{"q": $query}'). Credentials belong on an attached account, never inline in a header value.
(#snap_1) TransformMapper: Projects the useful part of the response onto '$content'. Keep the shape small - everything here is fed back into the agent's context on every iteration.
"""

from slpy.modules.Pipeline.Pipeline import ParamTable, Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.APISuiteHTTPClient import APISuiteHTTPClient
from slpy.modules.Snap.TransformMapper import TransformMapper

p = Pipeline(label="TOOL_Search", purpose="Search about the topic with a query string")

p.tags = Tags(value=["tool"])

p.param_table = ParamTable(
    param=[
        ParamTable.ParamItem(
            key="query",
            required=True,
            data_type="string",
            description="The query of interest",
        )
    ]
)


snap_0 = APISuiteHTTPClient(
    label="HTTP Client",
    http_method="POST",
    uri="https://google.serper.dev/search",
    query_param=[],
    header=[
        APISuiteHTTPClient.HeaderItem(header_name_prop="X-API-KEY", header_val_prop=None),
        APISuiteHTTPClient.HeaderItem(header_name_prop="Content-Type", header_val_prop="application/json"),
    ],
    enable_debug=True,
    form_encode_space=False,
    prevent_urlencoding=False,
    http_entity=APISuiteHTTPClient.HttpEntity(
        binary_file=None,
        multipart_subtype="form-data",
        entity_type="raw",
        raw_entity=Expr('{"q": $query}'),
        multipart_form=[
            APISuiteHTTPClient.HttpEntity.MultipartFormItem(
                part_type="Text", part_key=None, part_value=None, part_content_type=None
            )
        ],
        url_encoded_form=[],
    ),
    pagination=APISuiteHTTPClient.Pagination(
        reuse_params_for_pagination=False,
        pagination_interval=0,
        has_next=Expr(None),
        next_url=Expr(None),
        max_page=None,
        override_uri=False,
        override_headers=[
            APISuiteHTTPClient.Pagination.OverrideHeadersItem(
                override_header_name=None, override_header_value=Expr(None)
            )
        ],
        override_params=[
            APISuiteHTTPClient.Pagination.OverrideParamsItem(override_param_name=None, override_param_value=Expr(None))
        ],
    ),
    client_properties=APISuiteHTTPClient.ClientProperties(
        redirects=APISuiteHTTPClient.ClientProperties.Redirects(
            allow_relative_redirect=True,
            follow_redirection=True,
            allow_circular_redirect=False,
            follow_original_method=False,
            max_redirect=10,
        ),
        output_props=APISuiteHTTPClient.ClientProperties.OutputProps(
            extract_entity=False,
            extract_entity_path=Expr("$.entity"),
            response_type="JSON",
            include_cookies=False,
            error_resp_to_errorview=True,
        ),
        connection=APISuiteHTTPClient.ClientProperties.Connection(
            disk_staging_prop=False,
            cookie_policy="RFC Lax",
            read_timeout=900,
            trust_all_certs=False,
            conn_timeout=30,
        ),
        retry=APISuiteHTTPClient.ClientProperties.Retry(
            max_retry=5,
            retry_interval=3,
            use_retry_after_header=True,
            auto_retry429=True,
            retry_condition="Connection Errors",
        ),
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = TransformMapper(
    label="Mapper - Output content",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('$entity.hasOwnProperty("organic") ? $entity.organic : $entity'),
                target_path="$content",
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
    src_view_id="outputResponse",
    src_view_label="Response",
    dst_view_id="input0",
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
