# Use SnapCode

## Start a SnapCode session

Open a terminal in any directory and run:

```
claude
```

Claude Code opens and SnapCode is ready. You interact entirely through the chat, no commands or
syntax to memorize.

## Build a pipeline

Enter a natural language prompt in English to describe your pipeline. Be specific about the data
source, the transformation, and the destination to get the best results without follow-up
questions.

Example:

```
Build a pipeline that reads customer orders from Salesforce,
filters cancelled ones, and writes the results to Snowflake
```

SnapCode generates the pipeline source file (`.py`) and translates it to the Platform format
(`.slp`). For transformations that can run locally, it also executes the pipeline against local
test data before deployment.

If SnapCode needs clarification, such as the Salesforce object to read, it asks a question. Answer
it and SnapCode continues automatically.

> **Tip:** The more specific your description, the fewer follow-up questions. Include field names,
> filter conditions, and object names upfront when you know them.

> **Note:** SnapCode finds your Snap accounts with `list_accounts` and binds the chosen one in the
> pipeline, so no binding step in SnapLogic Designer or Manager is needed. If you edit the account
> name in the `.py` file yourself, it must exactly match the account name on the platform.

## Deploy a pipeline

Inform SnapCode where to deploy the pipeline:

```
Deploy it to the SLDemo org, projects/your-name/your-project path
```

The first time you deploy in a session, SnapCode asks for:

- **Environment/Org:** Your SnapLogic organization name (for example, `snaplogic` or `SLDemo`)
- **Project path:** Path to store the pipeline (for example, `projects/your-name/your-project`)
- **Snaplex:** Runtime to use for validation

Before deploying, SnapCode shows the plan (org, project path, and Snaplex) and waits for you to
confirm. SnapCode offers to save these for the rest of the session. You can also include all three
upfront in your deploy message to skip the prompts.

SnapCode uploads the pipeline and validates it on the SnapLogic Platform. If validation fails, it
shows the error and fixes it automatically before redeploying, up to 5 times.

> **Note:** If your pipeline depends on child pipelines, deploy them first so they are available
> when the parent is validated. List them as per the following example:
>
> ```
> Deploy child_pipeline.slp, then parent_pipeline.slp to...
> ```

## Run a pipeline

```
Run it
```

SnapCode triggers the pipeline on the SnapLogic Platform and returns the execution status,
including per-Snap error details if it fails.

## Edit a pipeline

You can change a deployed pipeline in two ways:

- **Conversationally:** Ask SnapCode to make the change, for example:

  ```
  Fix the Mapper expression: subtotal should be qty × unit_price
  ```

  SnapCode edits the `.py` file and retranslates it. When you ask it to deploy, it shows the plan
  for you to confirm, then validates.
- **By editing the file directly:** Open the generated `.py` file in any text editor, make your
  changes, save, then prompt SnapCode:

  ```
  Deploy it
  ```

  SnapCode picks up your edited file and redeploys from it.

## Validate an existing pipeline

To validate a pipeline on the SnapLogic Platform without running it:

```
Validate pipeline.slp
```

SnapCode validates the file on the Platform and reports any errors with the Snap name and field that
caused the issue.

## Use a local file as pipeline input

To upload a local file to SLDB so a pipeline can read it:

```
Upload sales_data.csv to SLDB at /snaplogic/my-project/
```

Then reference that path in your pipeline description when building.

## Build a reusable expression library

Expression libraries let you define helper functions once and reuse them across pipelines.

```
Create a date helpers expression library: today's date, previous month start/end, ISO formatting
```

SnapCode generates a `.expr` file, and uploads it to SLDB when you deploy a pipeline that uses it.

## Where your files are stored

All generated files (`.py`, `.slp`, `.expr`) are created in your current working directory on your
local machine. They persist across sessions. They are regular files on disk.

To keep the generated files organized, you can:

- Prompt SnapCode at the start of a session to put files in a subfolder:

  ```
  Put all generated files in my-pipelines/salesforce-project/
  ```

- Install SnapCode and run `claude` from any project directory of your choice. The plugin makes
  SnapCode available from any directory. Refer to [Install SnapCode](install-snapcode.md).

## Known issues

| Limitation | Details |
|---|---|
| Snap accounts | SnapCode cannot create or configure Snap accounts directly. To create a new account or update credentials on an existing one, use SnapLogic Designer or Manager. |
| MFA sign-in | MFA is supported through browser sign-in (SSO), with `SNAPLOGIC_API_USER` and `SNAPLOGIC_API_PASS` cleared. On the first sign-in with MFA, the browser might not return to Claude Code. Sign in again, or copy the sign-in URL into your browser. |
| Projects | SnapCode cannot create project spaces or projects. Create them in Manager first; SnapCode can then deploy to them. |
| Where the CLIs run | The `snaplogic` and `slpy` commands are supported inside Claude Code only. To run one yourself, prefix it with `!` in the Claude Code session, for example `! snaplogic auth status`. |
| Pipeline promotion across environments | There is no built-in support for promoting pipelines between environments (for example, from development to staging to production). Each deploy targets one Environment (Org) and project path. To promote a pipeline, deploy it again to each target Environment (Org) separately. |
| Execution history | SnapCode can only show the status of the run it just triggered. It cannot retrieve logs or history from past executions. |
| Session state | Environment (Org), project path, and Snaplex preferences are remembered within a single session only. Each new `claude` session starts fresh and prompts for these settings on the first deploy. They are also cleared when the SnapLogic MCP server reconnects. |
| Local files only | SnapCode works with files in your current working directory. Keep your pipeline files in the folder where you run `claude`. |
| Snaps that cannot run locally | Enterprise connector Snaps: Salesforce, Snowflake, NetSuite, SAP, database connectors, and similar that require Platform connectivity and cannot execute locally. For these pipelines, SnapCode generates a local test segment that replaces the non-local Snaps with file readers and writers so that transformation logic can still be validated before deployment. |
