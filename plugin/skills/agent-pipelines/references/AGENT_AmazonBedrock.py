"""
Pipeline Name: AGENT_AmazonBedrock

Pipeline Summary: This is the **Amazon Bedrock provider variant** of the agent (driver) pipeline.
Prompt generators run first (system prompt, then user prompt), then one or more *function generator*
snaps chained in series to accumulate the `$tools` payload, then a Mapper that flattens the nested
document into the three fields the agent snap reads, then the agent snap that runs the
conversation/tool-call loop, then a Mapper that projects the answer text. Use this variant when the
user wants Bedrock (or says nothing and the project is Bedrock-backed); use AGENT_OpenAI.py for
OpenAI. Also adapt this file for the **Gemini** and **Vertex Gemini** agents: their snaps carry the
system prompt as an agent property too ('advanced_prompt_configuration.system_prompt'), so they need
this three-row Mapper, not AGENT_OpenAI.py's two-row one. All tool pipelines required by the agent must be listed in the
LLMUtilitiesMultiPipelineFunctionGenerator (snap_2) under 'pipeline_section'. The driver is tagged
`agent`.

Why the Bedrock variant needs the Mapper: Bedrock Converse carries the system prompt in a separate
top-level request field, not as a message role - its prompt generator's role enum is USER/ASSISTANT
only, with no SYSTEM (do not "correct" it). So the system prompt is generated with
'advanced_mode=False', which emits a plain `prompt` string, and is routed to the agent snap's own
'system_prompt' property. Only the user prompt runs with 'advanced_mode=True' to build the `messages`
array. The Mapper (snap_3) exists because each upstream snap nests the previous document under
`original`, leaving the agent's three inputs at three different depths.

(#snap_0) AmazonBedrockLLMAmazonBedrockPromptGenerator: The system prompt - defines the agent's role, capabilities and constraints. 'editable_content' must be changed (think of it as assigning a role to the agent). It comes FIRST and uses 'advanced_mode=False' so it emits a `prompt` string rather than joining the `messages` array; 'role' is ignored in this mode.
(#snap_1) AmazonBedrockLLMAmazonBedrockPromptGenerator: Passes the end-user message into the agent, role='USER', 'advanced_mode=True'. Its template is `{{{original.msg}}}`, because snap_0 nested the pipeline's input under `original` and snap_1's own input has no `messages` key yet, so snap_1 resolves against the document root. (Contrast AGENT_OpenAI.py, where snap_0 does emit `messages` and snap_1 therefore resolves against `$original`, making the template a bare `{{{msg}}}`.) No changes required for a typical setup.
(#snap_2) LLMUtilitiesMultiPipelineFunctionGenerator: Registers **all** tool pipelines the agent may call. Configure each tool via 'pipeline_section', where each 'LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem' points to a tool pipeline.
(#snap_3) TransformMapper: Flattens the nested document into the three fields the agent snap reads. Copy this snap and snap_4 together as one unit - the agent's payload expressions only resolve when this Mapper is upstream of it. 'null_safe_access=False' is deliberate: a depth mistake errors the document instead of silently mapping null.
(#snap_4) AmazonBedrockLLMAmazonBedrockConverseAPIAgent: Executes the conversation loop and tool calls via Bedrock. 'agent_execution_configuration.iteration_limit' controls the max number of reasoning/tool-call iterations (schema minimum 1, default 10, no maximum). Increase it for more complex multi-step tasks. Keep 'reuse_pipeline=False' unless every registered tool pipeline is Ultra compatible - otherwise the tool call hangs and the agent times out. 'model_name' must be a model the attached Bedrock account serves. Its output document also carries an 'sl_agent_log' field, which is the execution log the Agent Visualizer renders.
(#snap_5) TransformMapper: Projects the agent's answer text onto `$response`. 'pass_through=True' keeps 'sl_agent_log' intact for the Agent Visualizer. The `[0]` index is deliberately unguarded: if the agent stops on 'iteration_limit' mid-tool-call the final turn can carry no text, and failing the document there is better than handing the caller a null `$response`, which is the silent-empty-answer failure this topology exists to prevent.
"""

from slpy.modules.Pipeline.Pipeline import Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.AmazonBedrockLLMAmazonBedrockConverseAPIAgent import (
    AmazonBedrockLLMAmazonBedrockConverseAPIAgent,
)
from slpy.modules.Snap.AmazonBedrockLLMAmazonBedrockPromptGenerator import (
    AmazonBedrockLLMAmazonBedrockPromptGenerator,
)
from slpy.modules.Snap.LLMUtilitiesMultiPipelineFunctionGenerator import (
    LLMUtilitiesMultiPipelineFunctionGenerator,
)
from slpy.modules.Snap.TransformMapper import TransformMapper

p = Pipeline(label="AGENT_AmazonBedrock")

p.tags = Tags(value=["agent"])


snap_0 = AmazonBedrockLLMAmazonBedrockPromptGenerator(
    label="System Prompt",
    prompt_template="Context Q & A",
    editable_content="You are a helpful assistant. Use the available tools to answer the user's question.",
    advanced_mode=False,
    name=None,
    content=None,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = AmazonBedrockLLMAmazonBedrockPromptGenerator(
    label="User Prompt",
    prompt_template="Context Q & A",
    editable_content="{{{original.msg}}}",
    advanced_mode=True,
    role="USER",
    name=None,
    content=None,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_2 = LLMUtilitiesMultiPipelineFunctionGenerator(
    label="Multi Pipeline Function Generator",
    pipeline_section=[
        LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(pipeline_path="TOOL_Search", strict_mode=False)
    ],
    aggregated_pipeline_path=None,
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
            TransformMapper.Transformations.MappingTableItem(
                expression=Expr("$original.original.prompt"), target_path="$system_prompt"
            ),
        ],
    ),
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_4 = AmazonBedrockLLMAmazonBedrockConverseAPIAgent(
    label="Amazon Bedrock Converse API Agent",
    editable_content=None,
    include_cross_region_models=True,
    model_name="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    system_prompt=Expr("$system_prompt"),
    message_payload=Expr("$messages"),
    tool_payload=Expr("$tools"),
    agent_execution_configuration=AmazonBedrockLLMAmazonBedrockConverseAPIAgent.AgentExecutionConfiguration(
        iteration_limit=10, monitor_tool_call=True, parallelism=1, reuse_pipeline=False
    ),
    advanced_tool_configuration=AmazonBedrockLLMAmazonBedrockConverseAPIAgent.AdvancedToolConfiguration(
        tool_choice="AUTO", function_name=None, cache_tool=False
    ),
    model_parameters=AmazonBedrockLLMAmazonBedrockConverseAPIAgent.ModelParameters(
        budget_tokens=None,
        stop_sequences=None,
        temperature=None,
        maximum_tokens=None,
        thinking=False,
        top_p=None,
    ),
    advanced_prompt_configuration=AmazonBedrockLLMAmazonBedrockConverseAPIAgent.AdvancedPromptConfiguration(
        cache_system=False
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
                expression=Expr('jsonPath($, "$output.message.content[*].text")[0]'),
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
    src_view_label="LLM Base response",
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
