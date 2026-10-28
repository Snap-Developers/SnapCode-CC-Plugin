"""
Pipeline Name: AGENT_OpenAI

Pipeline Summary: This is the SnapLogic-authored reference agent (driver) pipeline, using the OpenAI
provider. It is the **same six-snap topology as AGENT_AmazonBedrock.py** with the OpenAI prompt
generator and agent snaps dropped in: prompt generators first (system prompt, then user prompt), then
one or more *function generator* snaps chained in series to accumulate the `$tools` payload, then a
Mapper that flattens the nested document into the fields the agent snap reads, then the agent snap
that runs the conversation/tool-call loop, then a Mapper that projects the answer text. Only the
system prompt's 'editable_content', the 'model_name', and the 'pipeline_section' entries are meant to
change; everything else is fixed-format boilerplate. The driver is tagged `agent`.

One thing genuinely differs from the Bedrock variant, and it is forced by the snaps: the OpenAI agent
snap has **no 'system_prompt' property**, so OpenAI carries the system prompt as a message at
role='DEVELOPER'. That means both prompt generators run with 'advanced_mode=True' here (Bedrock's
system prompt runs with 'advanced_mode=False' and is routed to the agent's own property), so this
Mapper has two rows where Bedrock's has three. Everything else - snap order, the Mapper's position,
and the agent's '$messages' / '$tools' payload expressions - is identical.

Adapt this file for the **Azure Foundry** and **OpenAI Responses** agents, whose snaps also have no
'system_prompt' property. The **Gemini** and **Vertex Gemini** agents do have one
('advanced_prompt_configuration.system_prompt'), so adapt AGENT_AmazonBedrock.py for those two.

(#snap_0) OpenAILLMOpenAIPromptGenerator: The system prompt - defines the agent's role, capabilities and constraints. 'editable_content' must be changed (think of it as assigning a role to the agent). For the OpenAI provider this snap uses role='DEVELOPER'; it comes FIRST, before the user prompt.
(#snap_1) OpenAILLMOpenAIPromptGenerator: Passes the end-user message into the agent, role='USER'. Its template is `{{{msg}}}`, NOT `{{{original.msg}}}` as in the Bedrock variant. The reason is snap_1's own behaviour, not snap_0's: snap_0 emitted a `messages` key, and a generator whose input already has one resolves its template against `$original` instead of the root. snap_0 itself only nested the input document under `original` - it re-rooted nothing. No changes required for a typical setup.
(#snap_2) LLMUtilitiesMultiPipelineFunctionGenerator: Registers **all** tool *pipelines* the agent may call. Configure each tool via 'pipeline_section', where each 'LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem' points to a tool pipeline. Two other function generators exist for non-pipeline tool sources - see the note at the bottom of this docstring.
(#snap_3) TransformMapper: Flattens the nested document into the fields the agent snap reads. Copy this snap and snap_4 together as one unit - the agent's payload expressions only resolve when this Mapper is upstream of it. 'null_safe_access=False' is deliberate: a depth mistake errors the document instead of silently mapping null.
(#snap_4) OpenAILLMOpenAIChatCompletionsAgent: Executes the conversation loop and tool calls. 'agent_execution_configuration.iteration_limit' controls the max number of reasoning/tool-call iterations; increase it for more complex multi-step tasks. Keep 'reuse_pipeline=False' unless every registered tool pipeline is Ultra compatible - otherwise the tool call hangs and the agent times out. 'model_name' must be set to the model the attached OpenAI account serves. Its output document also carries an 'sl_agent_log' field, which is the execution log the Agent Visualizer renders.
(#snap_5) TransformMapper: Projects the agent's answer text onto `$response`. 'pass_through=True' keeps 'sl_agent_log' intact for the Agent Visualizer. The `[0]` index is deliberately unguarded: if the agent stops on 'iteration_limit' mid-tool-call the final turn can carry no text, and failing the document there is better than handing the caller a null `$response`, which is the silent-empty-answer failure this topology exists to prevent.

Other tool sources: if the user asks for an APIM service or an OpenAPI spec as a tool source rather
than (or as well as) tool pipelines, chain 'LLMUtilitiesAPIMFunctionGenerator' or
'LLMUtilitiesOpenAPIFunctionGenerator' in series with snap_2 - each adds to `$tools`. Both have
required fields with no usable default, so only add one when you have real values for those fields;
an unconfigured generator fails validation. Substitute the user's real values here - these are
placeholders, and a generator left with these literals is as broken as one left empty:

    snap_2b = LLMUtilitiesAPIMFunctionGenerator(
        label="APIM Tools",
        project_path="/ConnectFasterInc/projects/MyProject",
        service_name="customer-api",
        service_version="1.0",
        base_url="https://elastic.snaplogic.com/api/1/rest/slsched/feed/ConnectFasterInc/projects/MyProject/customer-api",
        aggregate_input=False,
        execution_mode="Validate & Execute",
        error_behavior="fail",
    )

    snap_2c = LLMUtilitiesOpenAPIFunctionGenerator(
        label="OpenAPI Tools",
        input_type="URL",
        openapi_url="https://api.example.com/v1/openapi.json",
        base_url="https://api.example.com/v1",
        aggregate_input=False,
        execution_mode="Validate & Execute",
        error_behavior="fail",
    )

APIM requires 'project_path', 'service_name', 'service_version' and 'base_url'. OpenAPI requires
'input_type' and 'base_url', plus the spec field that matches the 'input_type' you chose:
'URL'->'openapi_url', 'File'->'openapi_file', 'Text editor'->'openapi', 'Input document'->neither.
Keep 'aggregate_input=False' on every function generator - aggregate mode emits no `original`
wrapper and the Mapper's payload expressions stop resolving.
"""

from slpy.modules.Pipeline.Pipeline import Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.LLMUtilitiesMultiPipelineFunctionGenerator import (
    LLMUtilitiesMultiPipelineFunctionGenerator,
)
from slpy.modules.Snap.OpenAILLMOpenAIChatCompletionsAgent import (
    OpenAILLMOpenAIChatCompletionsAgent,
)
from slpy.modules.Snap.OpenAILLMOpenAIPromptGenerator import (
    OpenAILLMOpenAIPromptGenerator,
)
from slpy.modules.Snap.TransformMapper import TransformMapper

p = Pipeline(label="AGENT_OpenAI")

p.tags = Tags(value=["agent"])


snap_0 = OpenAILLMOpenAIPromptGenerator(
    label="System Prompt",
    prompt_template="Context Q & A",
    editable_content="You are a helpful assistant. Use the available tools to answer the user's question.",
    advanced_mode=True,
    role="DEVELOPER",
    name=None,
    content=Expr(None),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = OpenAILLMOpenAIPromptGenerator(
    label="User Prompt",
    prompt_template="Context Q & A",
    editable_content="{{{msg}}}",
    advanced_mode=True,
    role="USER",
    name=None,
    content=Expr(None),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_2 = LLMUtilitiesMultiPipelineFunctionGenerator(
    label="Multi Pipeline Function Generator",
    pipeline_section=[
        LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(pipeline_path="TOOL_Search", strict_mode=False)
    ],
    aggregated_pipeline_path=Expr(None),
    aggregated_strict_mode=False,
    aggregate_input=False,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_3 = TransformMapper(
    label="Prepare Agent Payload",
    null_safe_access=False,
    pass_through=False,
    transformations=TransformMapper.Transformations(
        mapping_root="$",
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(expression=Expr("$tools"), target_path="$tools"),
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("$original.messages"), target_path="$messages"
            ),
        ],
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_4 = OpenAILLMOpenAIChatCompletionsAgent(
    label="OpenAI Chat Completions Agent",
    editable_content=None,
    model_name="gpt-4o",
    message_payload=Expr("$messages"),
    tool_payload=Expr("$tools"),
    output_handling=OpenAILLMOpenAIChatCompletionsAgent.OutputHandling(store=False),
    agent_execution_configuration=OpenAILLMOpenAIChatCompletionsAgent.AgentExecutionConfiguration(
        iteration_limit=10, monitor_tool_call=True, parallelism=1, reuse_pipeline=False
    ),
    advanced_tool_configuration=OpenAILLMOpenAIChatCompletionsAgent.AdvancedToolConfiguration(
        tool_choice="AUTO", function_name=None, parallel_tool_call=True
    ),
    model_parameters=OpenAILLMOpenAIChatCompletionsAgent.ModelParameters(
        stop_sequences=None,
        temperature=None,
        reasoning_effort="medium",
        maximum_tokens=None,
        top_p=None,
    ),
    advanced_prompt_configuration=OpenAILLMOpenAIChatCompletionsAgent.AdvancedPromptConfiguration(json_mode=False),
    advanced_response_configuration=OpenAILLMOpenAIChatCompletionsAgent.AdvancedResponseConfiguration(
        structured_output=Expr(None)
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_5 = TransformMapper(
    label="Extract Response",
    null_safe_access=False,
    pass_through=True,
    transformations=TransformMapper.Transformations(
        mapping_root="$",
        mapping_table=[
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr('jsonPath($, "$choices[*].message.content")[0]'),
                target_path="$response",
            )
        ],
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
    dst_view_id="input0",
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
    src_view_label="Chat completion view",
    dst_view_id="input0",
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
