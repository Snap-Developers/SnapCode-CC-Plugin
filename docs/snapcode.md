# SnapCode

SnapCode is a code-first, developer-oriented complement to SnapLogic Designer. While SnapLogic
Designer provides a visual canvas, SnapCode gives you a conversational workflow where pipelines are
authored as code and deployed directly to your SnapLogic Org/Environment.

Use SnapCode to:

- Generate pipelines based on natural language prompts in English
- Discover and bind Snap accounts to pipelines automatically
- Deploy pipelines to your SnapLogic environment and project path
- Validate and run pipelines and check execution status
- Edit pipelines conversationally or modify the source `.py` file directly
- Build and upload reusable expression libraries
- Validate pipelines against the SnapLogic Platform before running them

To install it, see [Install SnapCode](install-snapcode.md).

## How SnapCode works

SnapCode connects Claude Code to your SnapLogic control plane (`SNAPLOGIC_BASE_URL`) through three
parts, all set up by the plugin:

- The SnapLogic MCP server (`plugin:snapcode:snaplogic`): Snap discovery, and Platform operations
  such as deploying, validating, and running pipelines and uploading files.
- The `slpy` CLI: translates, validates, and runs pipelines locally on your machine.
- The `snaplogic` CLI: browser sign-in, installing `slpy`, and lookups such as your organizations.

When you describe a pipeline, SnapCode usually goes through these steps:

1. **Discovers Snaps:** Looks up the correct Snap names, parameters, and connection rules from the
   SnapLogic Snap catalog.
2. **Discovers and binds Snap accounts:** If the pipeline requires a Snap account, looks up
   available accounts using `list_accounts` and binds the chosen one directly into the pipeline
   source file.
3. **Generates a pipeline source file (`.py`):** Writes the pipeline in SLPy, a readable
   Python-like format that serves as your source of truth.
4. **Translates to the Platform format (`.slp`):** Converts the `.py` source into the native
   SnapLogic JSON format required for deployment.
5. **Runs a local test (when the pipeline has logic to test):** Executes the pipeline locally
   against local test data for the supported Snaps to verify transformation logic before anything
   reaches the Platform.
6. **Deploys to your Environment:** After you confirm, uploads the `.slp` file to the org and
   project path you choose.
7. **Validates on the SnapLogic Platform:** Runs the pipeline validation equivalent to clicking
   **Validate** in Designer.

Knowledge of Snap names or parameter schemas is not required. SnapCode handles Snap discovery and
pipeline generation automatically. The generated `.py` file is available for direct editing at any
time.

### File types

SnapCode works with the following file types, stored locally on your machine:

| Extension | Description |
|---|---|
| `.py` | SLPy pipeline source: Readable, editable Python-like syntax. This is your source of truth. Edit this file to change a pipeline. |
| `.slp` | Translated pipeline: SnapLogic's native JSON format. Generated from the `.py` file, and regenerated before every deploy. |
| `.expr` | Expression library: Reusable functions that can be shared across pipelines. |

### SnapCode vs. SnapLogic Designer

The following table compares how SnapCode and SnapLogic Designer perform equivalent pipeline
development actions:

| SnapLogic Designer | SnapCode |
|---|---|
| Drag Snaps onto a visual canvas | Describe the pipeline using natural language prompts in English |
| Configure each snap in the canvas | SnapCode looks up correct parameters automatically |
| Edit a snap by clicking it on the canvas | Edit the `.py` file directly, or ask SnapCode to change it |
| Save and validate on the Platform | Deploy the pipeline to the specified Environment and project |

> **Note:** Account binding is automated: SnapCode uses `list_accounts` to discover available
> accounts and binds the chosen one directly into the generated pipeline. The pipeline imports with
> the account already configured. No manual account binding step in SnapLogic Designer or Manager
> is required. SnapCode cannot create or configure accounts directly. To create a new account or
> update credentials on an existing one, use SnapLogic Designer or Manager. See
> [Known issues](use-snapcode.md#known-issues) for details.
