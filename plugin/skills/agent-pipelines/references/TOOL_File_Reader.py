"""
Pipeline Name: TOOL_File_Reader

Pipeline Summary: This is a minimal fixed-format file reader tool pipeline for reading one or more files. Like every tool it needs a description, an argument schema and the 'tool' tag. This one declares its argument with 'p.tool_input_parameters' (the Designer Tool tab's JSON Schema) instead of 'p.param_table'; the tool description is the schema's 'description'. The argument feeds the reader's file_folder, so without it the tool is callable but can never read anything.

(#snap_0) BinaryMultiFileReader: Reads the files named in selected_files and outputs their binary content. Each SelectedFilesItem is one file; file_folder takes the path and is an expression field, so an agent-supplied param must be Expr()-wrapped. All files in this component must be of the same data type — for example, if the files are PDFs, they should all be PDFs; if the user wants CSV files, then all files should be CSVs.
(#snap_1) PDFParser: This is the PDFParser, mainly used to convert the content from BinaryMultiFileReader into text. You can replace it with any other parser — for example, if the data source is a CSV file, it would use a CSVParser instead.
(#snap_2) FlowGate: Aggregates the result stream into a single document. OPTIONAL - SnapLogic's own tool references omit it. Keep it when the tool would otherwise return many documents and one is wanted; remove it (and its links) otherwise.
"""

from slpy.modules.Pipeline.Pipeline import Pipeline, Tags, ToolInputParameters
from slpy.modules.Pipeline.utils import OPEN_VIEW, Expr
from slpy.modules.Snap.BinaryMultiFileReader import BinaryMultiFileReader
from slpy.modules.Snap.FlowGate import FlowGate
from slpy.modules.Snap.PDFParser import PDFParser

p = Pipeline(
    label="TOOL_File_Reader",
    purpose="Read the text content of a PDF file. Provide the full file path or URL of the document to read.",
)

p.tags = Tags(value=["tool"])

p.tool_input_parameters = ToolInputParameters(
    value={
        "type": "object",
        "description": "Read the text content of a PDF file. Provide the full file path or URL of the document to read.",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Full path or URL of the file to read (e.g. sldb:///reports/q3.pdf).",
            },
        },
        "required": ["file_path"],
    }
)


snap_0 = BinaryMultiFileReader(
    label="Multi File Reader",
    selected_files=[BinaryMultiFileReader.SelectedFilesItem(file_folder=Expr("$file_path"))],
    retries=0,
    retry_interval=1,
    advanced_properties=[],
    execute_during_preview=True,
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_1 = PDFParser(
    label="PDF Parser",
    pdf_pages="",
    pdf_parser_type="Text extractor",
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

snap_2 = FlowGate(
    label="Gate",
    ignore_empty_stream=False,
    output_doc_content="All input documents",
    execution_mode="Validate & Execute",
    error_behavior="fail",
)

p.connect(
    src=snap_0,
    dst=snap_1,
    src_view_id="output0",
    dst_view_id="input0",
    src_output_type="binary",
    dst_input_type="binary",
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
    src=OPEN_VIEW.INPUT,
    dst=snap_0,
    src_view_id="OPEN_VIEW.INPUT",
    dst_view_id="input101",
    dst_view_label="input0",
    src_output_type="document",
    dst_input_type="document",
)
p.connect(
    src=snap_2,
    dst=OPEN_VIEW.OUTPUT,
    src_view_id="output0",
    dst_view_id="OPEN_VIEW.OUTPUT",
    src_output_type="document",
    dst_input_type="document",
)
