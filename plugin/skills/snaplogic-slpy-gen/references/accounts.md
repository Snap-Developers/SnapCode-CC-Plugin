## Account Configuration

A SnapLogic Account is a reusable credential asset referenced by snaps that need authentication. When a snap has `pm_account` in its parameters (visible via `pygen_get_snap_parameters`), it accepts an account.

There are two valid binding forms: a **static** binding to one specific account asset via `Account(...)`, and an **expression** binding resolved at runtime via `Expr(...)`.

### Finding an account

1. **Check the snap's accepted types** — the snap docstring lists `ref_class_id` enum values
2. **Discover accounts on the platform** — call `list_accounts(org, project_path)` and filter the results by `class_id` against the snap's enum

### Static binding — `Account(...)`
```python
from slpy.modules.Snap import Account

snap_0 = APISuiteHTTPClient(
    label='Call API', http_method='POST', uri='https://example.com',
    pm_account=Account(
        ref_class_id='com-snaplogic-snaps-apisuite-accounts-headerauthaccount',
        label='my-account'
        # no ref_id on a new binding — the platform resolves it on import once `label` locates the account
    )
)
```

Verified end to end: an existing account binding survives export → edit → re-import with `ref_id` left empty.

### Expression binding — `Expr(...)`

Resolved at runtime, typically from an expression library, so the same pipeline works across Dev/Test/Prod environments:

```python
snap_0 = APISuiteHTTPClient(
    label='Call API', http_method='POST', uri='https://example.com',
    pm_account=Expr('lib.env.httpClientAccount')
)
```

### Preservation rules when editing an existing pipeline

- **NEVER remove, rewrite, or "simplify" a `pm_account=Expr('lib.env.*')` binding** unless the user explicitly asks to change the account. It is a deliberate environment-independence mechanism, not a label — replacing it with a static account (or dropping it) breaks the pipeline in every other environment.
- Leave `pm_account` exactly as found on snaps whose accounts you weren't asked to touch.

### When No Account is Available

If no matching account is found, **do not block pipeline generation**. Generate the pipeline without `pm_account` and note in your summary that the pipeline needs an account configured before it can authenticate. The user can add the account later in the platform designer.

A static `Account(...)` must reference an account that already exists on the platform — account assets cannot be created from here (see the deploy skill's limitations).

### Rules

- **NEVER pass a bare string** (`pm_account="lib.env.acct"`) — the parser silently produces an empty account binding. Use `Expr(...)` for expression refs or `Account(...)` for static refs.
- **DO NOT** use pipeline parameters for accounts (e.g., `oauth_account='$_oauthAccount'`). Use `Account(...)` or `Expr(...)`.
- **DO NOT** hallucinate account names or UUIDs. Use only values returned by the discovery step above.
