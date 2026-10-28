---
name: mcp-server-pipelines
description: "MCP server pattern: build an MCP server pipeline plus the tool pipelines it exposes. MANDATORY before generating any MCP server, MCP tools, or 'expose pipelines as tools over MCP' request — the server is a fixed-format multi-pipeline bundle; do not derive the topology from memory."
tools: Read, Write, Bash, TodoWrite, Glob, Grep, mcp__snaplogic__pygen_query_pipeline_examples, mcp__snaplogic__pygen_query_snap_examples, mcp__snaplogic__pygen_validate_snap_names, mcp__snaplogic__pygen_get_snap_parameters, mcp__snaplogic__pygen_get_snap_documentation, mcp__snaplogic__pygen_validate_connections, mcp__snaplogic__pygen_list_snaps_by_category, mcp__snaplogic__pygen_get_snap_io_info, mcp__snaplogic__pygen_get_all_snap_names
---

# MCP Server Pipelines (Pipeline-as-Tool pattern)

An **MCP server** is not one pipeline — it is a **bundle**: one *server* pipeline plus one or more
*tool* pipelines, each in its **own `.py` file**. The server pipeline is registered (by the user,
manually) as an MCP Server asset and serves the two MCP protocol methods itself: `tools/list`
(returns the tools with their JSON schemas) and `tools/call` (dispatches to the requested tool
pipeline and returns its result). There is **no LLM, prompt generator, agent snap, or account** in
the server — dispatch is pure routing. A request like "build me an MCP server that exposes weather
and CRM lookups" means: generate the server AND every tool pipeline it registers. Generate every file in the bundle, **server first**.

Working examples are in `references/`: `MCP_Server_Pipeline_As_Tool.py` (the server),
`TOOL_Search.py` (minimal HTTP tool), and `TOOL_CRM_insight.py` (branching tool with a not-found
path). Read the server example before generating — the snap configurations are fixed-format
boilerplate that must be copied, not re-derived.

The reference covers the **Pipeline-as-Tool** source (`LLMUtilitiesMultiPipelineFunctionGenerator`),
but `MCPServerRouter` also accepts **OpenAPI**, **APIM**, and plain **Function Generator** upstream —
do not refuse those. Only the generator changes; the router → execute → union → mapper chain is the
same. But the **Server pipeline** rules below are written for the Multi Pipeline generator, and two
do not carry over: tools are registered via **`tool_path`** on the other three, not `pipeline_section`
(only Multi Pipeline has that kwarg), and the `input101` view id is this reference's, so confirm the
generator's own. `../agent-pipelines/references/AGENT_OpenAI.py` shows the OpenAPI and APIM classes
and their fields, but its instances are unconfigured placeholders — configure yours. Plain
`LLMUtilitiesFunctionGenerator` has no reference anywhere; read its parameters before emitting it.

`MCPClientMCPFunctionGenerator` is a *client* snap — it exposes a **remote** MCP server's tools to an
agent, so it belongs in an agent pipeline, not here. Re-exposing a remote MCP server through your own
is a gateway pattern with no reference; say so rather than guess it.

## Server pipeline

Fixed 5-snap topology; only the Function Generator's `pipeline_section` entries change per server:

```
OPEN_VIEW.INPUT
    → LLMUtilitiesMultiPipelineFunctionGenerator   (declares the tool list — one entry per tool)
    → MCPServerRouter                              (output0 "Tool list view" | output1 "Tool call view")
         output1 → FlowPipelineExecute             (runs the called tool dynamically)
    → FlowUnion                                    (list view → input0, tool result → input1)
    → TransformMapper "Remove Original"            (strips $original* keys)
    → OPEN_VIEW.OUTPUT
```

Rules — each of these is load-bearing, not style:

- **`p.tags = Tags(value=["mcp_server"])`** — without the tag the pipeline translates cleanly but
  cannot be registered as an MCP Server asset.
- Register every tool as a
  `LLMUtilitiesMultiPipelineFunctionGenerator.PipelineSectionItem(pipeline_path=..., strict_mode=False)`.
  `pipeline_path` is the tool pipeline's **label** (resolved within the same project), not a path.
- The Function Generator's open input view is **`input101`** with display label `input0` — copy the
  example's connection verbatim; it is not a typo.
- **Never set `aggregate_input=True`** on the Function Generator. It re-roots the inbound document
  under `original` only in the default (non-aggregate) mode; flipping it emits no `original` wrapper,
  so `MCPServerRouter(request=Expr("$original"))` below reads null and the server stops responding.
- `MCPServerRouter(request=Expr("$original"))` — fixed boilerplate. **output0 is the tools/list
  response, output1 is the tools/call request.** Swapping them produces a server that returns tool
  metadata when a client tries to execute a tool. Carry the `src_view_label`s ("Tool list view" /
  "Tool call view") on the connections.
- `FlowPipelineExecute(pipeline=Expr("$sl_tool_metadata.path"), snaplex_governor="SNAPLEX_WITH_PATH",
  executable_during_suggest=True)` — the dynamic dispatch binding. Never hardcode a tool path there,
  and never set `executable_during_suggest=False` (it breaks design-time tool discovery).
- Keep the final "Remove Original" mapper
  (`$.filter((value, key) => !key.startsWith("original"))`) — without it the MCP client sees the
  inbound request echoed back inside `original.*` keys.

## Tool pipelines

A tool pipeline for an MCP server is **the same contract as an AgentCreator tool** — the identical
pipeline serves both an agent driver and an MCP server. Three things are mandatory:

1. **`purpose=`** on `Pipeline(...)` — the tool description an LLM reads to decide when to call it.
2. **The tool's arguments**, declared in **one** place, never both:
   - **`p.tool_input_parameters`** — a JSON Schema, shown in Designer's Tool tab
     (`TOOL_CRM_insight.py`). It can express nesting, lists and enums.
   - **`p.param_table`** alone, with no schema (`TOOL_Search.py`): `required`, `data_type`
     (`"string"`, `"number"`, `"boolean"`) and `description` per param; omit `capture`/`value`.

   Arguments arrive on the tool's **input document**: snaps read required ones as `$arg`. An optional
   argument the client leaves out is **absent** from the document, and reading a missing field throws —
   even inside `$arg != null ? … : …`. Read every optional argument with `$.get('arg')` or
   `$.get('arg', default)`. `p.param_table` is
   also the pipeline's own parameter table, read as `_name`. With a schema, keep configuration such as
   a base URL there — the client never sees it. Without a schema, every `param_table` row is shown to
   the client as an argument, so keep configuration and secrets out of it.

   ```python
   p = Pipeline(label="TOOL_Weather", purpose="Get the weather forecast for a city")
   p.tool_input_parameters = ToolInputParameters(value={
       "type": "object",
       "description": "Get the weather forecast for a city",  # repeat purpose: the Function Generator reads it here
       "properties": {
           "city": {"type": "string", "description": "The city to get weather from"},
           "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"},
       },
       "required": ["city"],
   })  # Python True/False/None, not JSON true/false/null
   p.param_table = ParamTable(param=[ParamTable.ParamItem(key="api_base", value="https://api.example.com")])
   # In a snap: Expr("_api_base + '/forecast?q=' + $city + '&units=' + $.get('units', 'metric')")
   ```

3. **`p.tags = Tags(value=["tool"])`** — without it the tool is invisible to the Function Generator.

When editing an existing tool, keep the form it already uses. If it has `p.tool_input_parameters`,
never delete it — that empties the Tool tab on deploy — and update its `properties` and `required`
when you add, rename, or remove an argument.

Conventions:
- Name tools **`TOOL_<capability>`**; keep label, `pipeline_path`, and file stem aligned. Labels
  must match `^[A-Za-z][A-Za-z0-9_]{0,63}$` — no dashes, spaces, or leading digits.
- Project the useful part of the result onto **`$content`** in a final mapper and keep it small.
  Give every branch a result — a tool that can return an empty stream reads as a failure to the
  calling LLM (see the not-found branch in `TOOL_CRM_insight.py`).
- Both `OPEN_VIEW.INPUT` and `OPEN_VIEW.OUTPUT` must be connected.
- Credentials belong on an attached account, never inline in a header or URI.
- For more tool shapes (SQL query, document store, mail, file reading), activate the
  **agent-pipelines** skill and adapt its `TOOL_*` references — the contract is identical.

## Cross-file consistency (the #1 failure mode)

- Every `pipeline_section.pipeline_path` must **exactly match the `label=` of a tool pipeline you
  generated** (or an existing project pipeline the user named). Never invent a path; never leave a
  registered tool ungenerated.
- One pipeline per file; file stem = pipeline label.
- Before delivering, re-read the server's `pipeline_section` entries against the tool files you
  actually wrote. Missing tags, a dangling `pipeline_path`, and a hardcoded dispatch pipeline all
  translate cleanly and only fail at runtime, so translation passing is not evidence they are right.

## Delivery


Write one file per pipeline, **server first**, tools after. In your final summary:


1. The whole bundle must be imported into **one project** — the server's `pipeline_path` references
   only resolve when server and tools are saved side by side.
2. Tell the user that generation stops at the pipelines: they must **manually create the MCP Server
   asset** (pointing it at the server pipeline) **and configure its MCP policy** (authentication)
   before any MCP client can connect. Include this link:
   [MCP server setup](https://docs.snaplogic.com/mcp/mcp-server-setup.html).
