---
name: agent-pipelines
description: "AgentCreator pattern: build agent pipelines (driver + tool pipelines). MANDATORY before generating any agent, AI assistant, or tool pipeline — these are fixed-format multi-pipeline bundles; do not derive the topology from memory."
tools: Read, Write, Bash, TodoWrite, Glob, Grep, mcp__snaplogic__pygen_query_pipeline_examples, mcp__snaplogic__pygen_query_snap_examples, mcp__snaplogic__pygen_validate_snap_names, mcp__snaplogic__pygen_get_snap_parameters, mcp__snaplogic__pygen_get_snap_documentation, mcp__snaplogic__pygen_validate_connections, mcp__snaplogic__pygen_list_snaps_by_category, mcp__snaplogic__pygen_get_snap_io_info, mcp__snaplogic__pygen_get_all_snap_names
---

# Agent Pipelines (AgentCreator pattern)

An **agent pipeline** is not one pipeline — it is a **bundle**: one *driver* pipeline plus one or
more *tool* pipelines, each in its **own `.py` file**. The driver runs an LLM conversation loop and
calls the tools; each tool wraps one capability (an API call, a DB query, sending mail, reading
files). A request like "build me an agent that answers weather questions using a weather API" means:
generate the driver AND every tool pipeline it registers. This is an explicit multi-pipeline ask —
generate every file in the bundle, **driver first**.

Working examples for every shape described here are in `references/`, named by kind: **`AGENT_*`**
drivers (`AGENT_OpenAI.py`, `AGENT_AmazonBedrock.py`) and **`TOOL_*`** tools (the other 5). Read the
relevant example before generating — the snap configurations are fixed-format boilerplate that must be
copied, not re-derived. The set is deliberately small: one example per *shape*, not per technology.
Adapt the nearest one (a Snowflake tool is `TOOL_MySQL_Query.py` with a different Select snap).

## Driver pipeline

The driver has a fixed topology; only the **provider snaps** change. The system prompt comes first,
then the user prompt, then one or more *function generator* snaps **chained in series** to accumulate
`$tools`, then the provider's agent snap, then a Mapper that projects the answer text:

```
OPEN_VIEW.INPUT → <Provider>PromptGenerator  (system prompt FIRST, then user prompt,
               → <Provider>PromptGenerator    one snap each)
               → LLMUtilitiesMultiPipelineFunctionGenerator   (registers ALL tool pipelines)
               → TransformMapper              (flattens the nested document into the fields
                                               the agent snap reads)
               → <Provider>Agent                              (the conversation/tool-call loop)
               → TransformMapper              (projects the answer text onto $response)
               → OPEN_VIEW.OUTPUT
```

**Every variant is these six snaps in this order.** Changing provider means dropping in that
provider's prompt generator and agent snap — never adding, removing, or reordering a snap. The one
exception is an extra function generator (APIM / OpenAPI, see the rule below), which chains in series
at the function-generator position and moves nothing else. Pick the
variant from what the user asked for; default to Bedrock when they don't say and the project is
Bedrock-backed.

Two variants ship as references, and they differ in exactly one thing: **where the system prompt
travels.** The OpenAI agent snap has no `system_prompt` property, so OpenAI sends the system prompt as
a message; the Bedrock agent snap has one, and Bedrock Converse has no message role that can carry a
system prompt, so Bedrock sends it as a property. Everything downstream follows from that:

| | OpenAI (`AGENT_OpenAI.py`) | Amazon Bedrock (`AGENT_AmazonBedrock.py`) |
|---|---|---|
| Prompt / agent snaps | `OpenAILLMOpenAIPromptGenerator`, `OpenAILLMOpenAIChatCompletionsAgent` | `AmazonBedrockLLMAmazonBedrockPromptGenerator`, `AmazonBedrockLLMAmazonBedrockConverseAPIAgent` |
| System prompt snap | `advanced_mode=True`, `role='DEVELOPER'` — it joins the `messages` array | `advanced_mode=False` — it emits a `prompt` string the Mapper routes to the agent's property. That snap's role enum is `USER`/`ASSISTANT` only — there is no `SYSTEM`, and do not "correct" it to one; `role` is ignored entirely when `advanced_mode=False` |
| User prompt template | `{{{msg}}}` | `{{{original.msg}}}` |
| Payload Mapper rows | 2: `$tools`→`$tools`, `$original.messages`→`$messages` | 3: the same two, plus `$original.original.prompt`→`$system_prompt` |
| Agent boilerplate | `message_payload=Expr('$messages')`, `tool_payload=Expr('$tools')` | same, plus `system_prompt=Expr('$system_prompt')` |
| Account | OpenAI account | Bedrock account (`com-snaplogic-snaps-awsbedrock-awsbedrockaccount`) |

The two template and Mapper-row differences are **not style** — they fall out of the `advanced_mode`
table below. A non-advanced system prompt adds an `original.` level that an advanced one does not, and
an advanced generator resolves its own mustache scope differently depending on its own input. Take
both from the variant you picked; do not mix them.

Four more agent snaps exist and have **no reference file**. Which one you start from is decided by a
single question — does that snap have its own system-prompt property? If it does, it needs Bedrock's
three-row Mapper; if it does not, the system prompt travels as a message and it needs OpenAI's
two-row one. Keep the six-snap topology; only these fields differ and are not guessable, so check the
snap's parameters before emitting:

| Agent snap | Start from | Model field | Message field | System prompt | Tool config |
|---|---|---|---|---|---|
| `AzureOpenAILLMAzureAIFoundryChatCompletionsAgent` | `AGENT_OpenAI.py` | **`deployment_id`** | `message_payload` | prompt generator | **`tool_parameters`** |
| `GoogleGenAILLMGoogleGeminiAPIAgent` | **`AGENT_AmazonBedrock.py`** | `model_name` | **`contents`** | **`advanced_prompt_configuration.system_prompt`** | `advanced_tool_configuration` |
| `OpenAILLMOpenAIResponsesAPIAgent` | `AGENT_OpenAI.py` | `model_name` | `message_payload` | prompt generator, or **`advanced_prompt_configuration.instructions`** | `advanced_tool_configuration` |
| `GoogleGenAILLMGoogleVertexAIGeminiAPIAgent` | **`AGENT_AmazonBedrock.py`** | `model_name` **plus `model_location`** (the Vertex region) | **`contents`** | **`advanced_prompt_configuration.system_prompt`** | `advanced_tool_configuration` |

All four are supported — **do not refuse any of them.** `OpenAILLMOpenAIResponsesAPIAgent` also
accepts `built_in_tools`. The pinned catalog ships no doc page for `OpenAILLMOpenAIResponsesAPIAgent`
or `GoogleGenAILLMGoogleVertexAIGeminiAPIAgent`, so `pygen_get_snap_documentation` returns nothing for
those two — use `pygen_get_snap_parameters` instead of retrying. Prompt generators are per-provider and were renamed in the pinned catalog:
Google → `GoogleGenAILLMGoogleGenAIPromptGenerator`, Azure → `AzureOpenAILLMAzureAIFoundryPromptGenerator`
(**not** the old `AzureOpenAILLMAzureOpenAIPromptGenerator`, which no longer exists).
Never substitute a non-agent `...ToolCalling` snap: no plain-named one is left in the pinned catalog
and every survivor is deprecated by name.

Rules:
- The only free text is the **system prompt's `editable_content`** (the agent's role/constraints), the
  **`model_name`** (or `deployment_id`), and the Vertex agent's **`model_location`**. Everything else
  is boilerplate from the example.
- The payload expressions are **fixed, non-derivable boilerplate** — copy them verbatim from the
  variant you picked. They are expression fields: wrap them in `Expr(...)`. **Copy the payload Mapper
  and the agent snap together as one unit**, on every variant: `$messages`, `$tools` and (on Bedrock)
  `$system_prompt` only exist because that Mapper creates them, so an agent snap pasted without it
  reads nulls.
- **Always pass `reuse_pipeline=False` explicitly** in `agent_execution_configuration`, on every
  variant. Reuse only works when *every* registered tool pipeline is Ultra compatible; otherwise the
  tool call hangs and the agent times out. Omitting the kwarg is not safe — the default is `True` on
  **four of the six** agent snaps in the catalog: Gemini, Vertex Gemini, Azure Foundry and OpenAI
  Responses. Only Bedrock and OpenAI Chat Completions default to `False`, and those are exactly the
  two with a reference file — so every variant you have to adapt by hand is one that defaults unsafe.
- `agent_execution_configuration.iteration_limit` must be **≥ 1** (schema minimum; default 10, no
  maximum). Raise it for multi-step tasks.
- Register **every** tool pipeline as a
  `LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(pipeline_path=..., strict_mode=False)`.
- **Function generators chain in series**, each adding to `$tools`. `LLMUtilitiesMultiPipelineFunctionGenerator`
  is the one to use for tool pipelines. `LLMUtilitiesAPIMFunctionGenerator` and
  `LLMUtilitiesOpenAPIFunctionGenerator` exist for APIM services and OpenAPI specs — add one only when
  the user asked for that tool source *and* you have real values for its required fields
  (`project_path`, `service_name`, `service_version`, `base_url` for APIM; `base_url` plus one of
  `openapi_file`/`openapi_url`/`openapi` for OpenAPI). An unconfigured generator fails validation.
- **Never set `aggregate_input=True`** on a function generator whose downstream reads `$original` —
  aggregate mode emits no `original` wrapper and the agent's payload expressions stop resolving.
- **`p.tags = Tags(value=["agent"])`** on the driver.
- The account is **required for execution**. Follow `../snaplogic-slpy-gen/references/accounts.md`: use a
  matching `.slf` account if one exists; otherwise generate **without** `pm_account` and tell the user
  to attach one in Designer. Never emit `pm_account=''` or an `Account()` with empty fields.
- The agent snap's output document carries an **`sl_agent_log`** field — the execution log the Agent
  Visualizer renders. The *response* Mapper after the agent snap therefore uses `pass_through=True`
  so it survives. The *payload* Mapper before the agent snap is the opposite — `pass_through=False`,
  because the agent should receive only the three fields it reads.

### Advanced prompt output, and what it does to the document

`advanced_mode` on a prompt generator decides both what the snap emits and how deeply it nests what
came before. This is the single most common source of a wrong payload expression:

| `advanced_mode` | input state | output | nesting added |
|---|---|---|---|
| `False` | any | `{prompt: "<rendered string>"}`, upstream under `original` | **+1** |
| `True` | no `messages` key yet | `{messages: [msg]}`, upstream under `original` | **+1** |
| `True` | already has `messages` | appends to that array and re-roots expressions to `$original`; **keeps only `{messages, original}`** | **0** |

Three consequences:

1. `advanced_mode=False` → read **`prompt`** (a string). `True` → read **`messages`** (a list).
2. An `advanced_mode=True` generator **discards every other top-level field**. Never place one
   downstream of a function generator — it deletes `$tools`.
3. Where a `True` generator's mustache template resolves depends on **its own input**, and this is
   the row of the table people skip. With **no `messages` key yet** it resolves against the document
   root, so it must address whatever nesting upstream snaps already added — in the Bedrock variant
   the `advanced_mode=False` system prompt put the input under `original`, so the user prompt's
   template is `{{{original.msg}}}`. With a **`messages` key already present** it re-roots to
   `$original`, which cancels that nesting out — in the OpenAI variant the system prompt is itself
   `True`, so the user prompt's template is a bare `{{{msg}}}`. A generator never re-roots the
   *next* snap's scope; it only ever changes its own.

That is where the Bedrock Mapper's two different depths come from — `messages` sits one `original.`
level deep, `prompt` two:

```
input {msg}
 → System Prompt (advanced OFF) ⇒ {prompt, original:{msg}}                             # +1
 → User Prompt   (advanced ON)  ⇒ {messages, original:{prompt, original:{msg}}}        # +1
 → function generator           ⇒ {tools, original:{messages, original:{prompt, …}}}   # +1
 → Mapper: $tools→$tools | $original.messages→$messages | $original.original.prompt→$system_prompt
```

### Repairing an existing agent pipeline

When the user asks you to fix an agent pipeline rather than generate one, these are the defect
signatures and their corrections. All four came from real generated pipelines:

| Signature | Correction |
|---|---|
| Bedrock agent with `system_prompt` set to `jsonPath($, "original.messages[*].content")` | The system prompt never reaches Bedrock. Retopologise to the Bedrock shape above: system prompt first at `advanced_mode=False`, payload Mapper, `system_prompt=Expr('$system_prompt')`. |
| A system prompt generator at `role='ASSISTANT'` | Bedrock has no message role that carries a system prompt — an `ASSISTANT` turn is a *prefill*. Move it to the agent snap's `system_prompt` property. |
| `reuse_pipeline=True` | Set it to `False` unless the user confirms every tool pipeline is Ultra compatible. |
| No Mapper between the function generator and the agent snap | Add it. Every variant has one; without it the agent's payload expressions resolve against the wrong depth. |
| Agent snap wired straight to `OPEN_VIEW.OUTPUT` | Add the response Mapper (`pass_through=True`), or the user sees the raw provider document and reads it as "no result". |

## Tool pipelines

Each tool is a separate small pipeline the driver calls. Three things make a pipeline a tool — all
three are mandatory:

1. **`purpose=`** on `Pipeline(...)` — this is the tool description the LLM agent reads to decide
   when to call it. Write it detailed and specific.
2. **The tool's arguments** — the inputs the agent must supply when calling the tool (NOT the same
   as any snap's own parameters). The agent passes them on the tool's input document, so snaps read
   required ones as `'$arg_name'` inside expression fields. An optional argument the agent leaves out
   is **absent** from the document, and reading a missing field throws — even inside
   `$arg != null ? … : …` — so read every optional argument with `$.get('arg')` or
   `$.get('arg', default)`. Declare arguments in **one** of two places, never both:

   - **`p.tool_input_parameters`** — a JSON Schema, shown in Designer's Tool tab (`TOOL_File_Reader.py`).
     It can express nesting, lists and enums. Repeat the `purpose` text as the schema's
     `description`: when this schema is present, the Function Generator takes the tool description
     from it, not from `purpose`. Write it with Python literals (`True`/`False`/`None`, not
     `true`/`false`/`null`):

     ```python
     from slpy.modules.Pipeline.Pipeline import Pipeline, ParamTable, Tags, ToolInputParameters

     p.tool_input_parameters = ToolInputParameters(
         value={
             "type": "object",
             "description": "Get the weather forecast for a city",
             "properties": {"city": {"type": "string", "description": "The city to get weather from"}},
             "required": ["city"],
         }
     )
     # Pipeline parameters stay in param_table, are read as '_api_base', and are NOT shown to the agent.
     p.param_table = ParamTable(param=[ParamTable.ParamItem(key='api_base', value='https://api.example.com')])
     # In a snap: Expr("_api_base + '/forecast?q=' + $city")
     ```

   - **`p.param_table`** alone, with no schema (`TOOL_Search.py`). Every row then becomes a tool
     argument shown to the agent, so do not put configuration or secrets in it:

     ```python
     p.param_table = ParamTable(
         param=[
             ParamTable.ParamItem(key='city', required=True, data_type='string',
                                  description='The city to get weather from'),
         ]
     )
     ```

   `p.param_table` itself is the pipeline's parameter table, read in expressions as `_name`. With a
   schema, it holds only those pipeline parameters (base URLs, environment settings) and the agent
   never sees them. **Always use the assignment form** — the `Pipeline(param_table=[...])` kwarg form
   silently produces an empty table. Leave `capture` at its default (`False`) — that is what
   SnapLogic's own tool pipelines do. The fixed-format DB and mail references ship `capture=True`;
   copy them verbatim rather than "correcting" it.

   When editing an existing tool, keep the form it already uses. If it has
   `p.tool_input_parameters`, never delete it — that empties the Tool tab on deploy — and update its
   `properties` and `required` when you add, rename, or remove an argument.

3. **`p.tags = Tags(value=["tool"])`** — the AI-capability tag. Every SnapLogic-authored tool pipeline
   carries it and the Designer tool picker keys off it, so a tool without it can translate cleanly yet
   be unusable from the driver.

Conventions worth following from SnapLogic's own references:
- Name tools `TOOL_<capability>` (`TOOL_Search`, `TOOL_weather_forecast`) so a bundle reads clearly.
  Any identifier-style label works, but keep label, `pipeline_path`, and file stem aligned.
- Project the useful part of the result onto **`$content`** in a final mapper, and keep it small —
  every tool result re-enters the agent's context on each iteration.
- **`FlowGate` is optional.** It aggregates the result stream into one document. SnapLogic's own tool
  pipelines omit it, so do not add it reflexively — use it only when a tool would otherwise return
  many documents and the caller wants one. When you drop it, drop its links too.

Tool examples to copy from, one per shape:

| Shape | Example | What it teaches |
|---|---|---|
| HTTP API call | `TOOL_Search.py` | POST with a JSON body, params via `Expr`, result projected onto `$content` |
| SQL query | `TOOL_MySQL_Query.py` | Fixed-format Select config (set `table_name`); ships `capture=True` — copy verbatim; trailing `FlowGate` |
| Document store | `TOOL_MongoDB_Query.py` | Same shape without SQL — swap the Select snap for any other DB |
| Send mail | `TOOL_Mail_Sender.py` | An account attached in Designer, never emitted in code |
| Read + parse files | `TOOL_File_Reader.py` | Multi-snap chain: reader → parser (swap `PDFParser` for the real format); arguments declared with `p.tool_input_parameters` |

## Cross-file consistency (the #1 failure mode)

- Every `pipeline_section.pipeline_path` must **exactly match the `label=` of a tool pipeline you
  generated** (or an existing project pipeline the user named). A bare name resolves within the same
  project. Never invent a path; never leave a registered tool ungenerated.
- A tool label / `pipeline_path` must match **`^[A-Za-z][A-Za-z0-9_]{0,63}$`** — starts with a letter,
  letters/digits/underscores only, max 64 chars. **No dashes, no spaces, no leading digit**: the model
  provider rejects the derived function name and translation does not catch it.
- One pipeline per file; file stem = pipeline label.

## Delivery


Write one file per pipeline, **driver first**, tools after. The whole bundle must be imported into
**one project** — the driver's `pipeline_path` references only resolve when driver and tools sit
side by side.
