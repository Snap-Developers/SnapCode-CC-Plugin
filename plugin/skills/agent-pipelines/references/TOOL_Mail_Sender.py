"""
Pipeline Name: TOOL_Mail_Sender

Pipeline Summary: This is a minimal fixed-format mail sender tool pipeline. The configuration, including all parameters in the param_table, must not be modified or extended. It sends mail. The 'purpose' field in the pipeline must always be written. It should clearly describe the function of this tool so that the agent can understand what the tool does. A detailed and specific description is encouraged.

(#snap_0) EmailSender: This component uses a fixed-format configuration that must not be modified, except for the email_type field. The required SMTP account (pm_account) is attached in Designer — do not emit it in code; see the accounts guidance in the skill. The email_type supports three options: Plain text, HTML text, and HTML table. The user must be asked which format they prefer. If the user selects HTML text, the value should be set to email_type='HTML text'; if the user selects Plain text, use email_type='Plain text'; if the user selects HTML table, use email_type='HTML table'.
"""

from slpy.modules.Pipeline.Pipeline import ParamTable, Pipeline, Tags
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.EmailSender import EmailSender

p = Pipeline(
    label="TOOL_Mail_Sender",
    purpose="This tool sends an email message to one or more recipients. It accepts input fields for to, cc, bcc, subject, and body, then constructs and delivers the email accordingly. Always supply every field; pass an empty string for cc or bcc when there are none.",
)
p.tags = Tags(value=["tool"])

p.param_table = ParamTable(
    param=[
        ParamTable.ParamItem(
            key="to",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="One or more primary recipient email addresses. The email is delivered to these addresses and they are visible to all recipients. Accepts a single address or a comma-separated list (e.g., alice@example.com, bob@example.org). Each value should be a valid email address string.",
        ),
        ParamTable.ParamItem(
            key="subject",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="Subject line of the email. This is a short text summary that appears in the recipient’s inbox and helps them understand the purpose of the message before opening it. Keep it concise but descriptive (e.g., “Monthly report for October 2025”).",
        ),
        ParamTable.ParamItem(
            key="body",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="Main content of the email message in plain text. This is what the recipient reads after opening the email. It can include multiple lines, paragraph breaks, and dynamic values passed from upstream pipeline data (for example, using expression variables to personalize the message).",
        ),
        ParamTable.ParamItem(
            key="cc",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="List of 'carbon copy' recipients who should receive a visible copy of the email in addition to the primary recipients. Accepts a single email address or a comma-separated list. If no CC recipients are provided, this field should return an empty string ().",
        ),
        ParamTable.ParamItem(
            key="bcc",
            value="",
            capture=True,
            required=True,
            data_type="string",
            description="List of 'blind carbon copy' recipients. These recipients receive a hidden copy of the email, and their addresses are not visible to other recipients. Accepts a single email address or a comma-separated list. If no BCC recipients are provided, this field should return an empty string ().",
        ),
    ]
)


snap_0 = EmailSender(
    label="Email Sender",
    executable_during_suggest=False,
    to=Expr("$to"),
    cc=Expr("$cc"),
    bcc=Expr("$bcc"),
    from_=None,
    subject=Expr("$subject"),
    email_type="Plain text",
    body=Expr("$body"),
    attachments=[],
    table_data_path=None,
    batch_size=100,
    pass_through=False,
    retries=3,
    execution_mode="Execute only",
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
    dst=OPEN_VIEW.OUTPUT,
    src_view_id="output0",
    dst_view_id="OPEN_VIEW.OUTPUT",
    src_output_type="document",
    dst_input_type="document",
)
