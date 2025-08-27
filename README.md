# OASIS CSAF Sandbox

![OASIS Logo](csaf/v2.1/csd01/images/OASISLogo-v3.0.png)

## Overview

This repository contains the OASIS Common Security Advisory Framework (CSAF) development sandbox, featuring automated workflows for processing Markdown documents into professional HTML and PDF outputs. The repository is designed to support OASIS specification development with automated formatting, conversion, and packaging workflows.

## Repository Structure

```
oasis/csaf-sandbox/
├── .github/                          # GitHub Actions configuration
│   ├── src/                         # Source code for processing scripts
│   │   ├── fix_html_for_pdf.py      # HTML preprocessor for PDF optimization
│   │   ├── step_2_convert_html_to_pdf.py  # HTML to PDF conversion
│   │   ├── step_1_markdown_to_html_converter_V3_0.py  # Markdown to HTML converter
│   │   └── requirements_pdf.txt      # Python dependencies
│   ├── scripts/                     # Shell scripts for workflow execution
│   │   ├── step_1_format_md_and_convert_to_html_v3_0.sh
│   │   ├── step_2_convert_html_to_pdf_V2_0.sh
│   │   └── step_2_convert_html_to_pdf_FIXED.sh
│   └── workflows/                   # GitHub Actions workflow definitions
│       ├── step_1_format_md_and_convert_to_html.yml
│       ├── step_2_convert_md_to_html_pdf_final.yml
│       └── step_3_create_zipfile.yml
├── csaf/                           # CSAF specification content
│   └── v2.1/
│       └── csd01/                  # Committee Specification Draft 01
│           ├── csaf-v2.1-csd01.md  # Source Markdown specification
│           ├── csaf-v2.1-csd01.html  # Generated HTML
│           ├── csaf-v2.1-csd01.pdf   # Generated PDF
│           └── images/             # Associated images and assets
└── .githooks/                      # Git hooks for metadata management
```

## Automated Workflows

### 1. Markdown to HTML Conversion (`step_1_format_md_and_convert_to_html.yml`)

**Purpose**: Formats and converts Markdown documents to HTML with proper styling and metadata.

**Features**:
- Prettier-based Markdown formatting
- Pandoc conversion with custom CSS styling
- OASIS branding and metadata integration
- Automatic link processing and image localization
- Preserves document structure and anchor links

**Inputs**:
- `sync_path`: Directory path containing the Markdown file (e.g., `csaf/v2.1/csd01`)
- `modify_date`: Document modification date in `yyyy-mm-dd` format

**Key Components**:
- Sets up Node.js and Python environments
- Installs Prettier for Markdown formatting
- Uses custom Python scripts for HTML generation
- Applies OASIS CSS styling for professional appearance
- Updates file modification timestamps

### 2. HTML to PDF Conversion (`step_2_convert_md_to_html_pdf_final.yml`)

**Purpose**: Converts HTML documents to professional PDF format with enhanced code block formatting.

**Features**:
- Uses wkhtmltopdf for high-quality PDF generation
- Preserves original CSS styling and anchor links
- Enhanced monospace formatting for code blocks
- Portrait orientation with optimized margins
- Professional headers and footers with metadata

**Inputs**:
- `sync_path`: Directory path containing the HTML file
- `modify_date`: Document modification date in `yyyy-mm-dd` format

**Key Components**:
- Installs patched wkhtmltopdf with font support
- Preprocesses HTML to optimize code block rendering
- Applies targeted CSS improvements without overriding OASIS styles
- Generates PDF with proper page layout and typography

### 3. ZIP Package Creation (`step_3_create_zipfile.yml`)

**Purpose**: Creates distribution packages containing all specification files.

**Features**:
- Packages all files in a directory into a ZIP archive
- Maintains consistent naming conventions
- Updates file timestamps for release consistency
- Automatically commits and pushes the generated package

**Inputs**:
- `latest_version_path`: Directory to package
- `modify_date`: Timestamp for packaged files

**Key Components**:
- Creates ZIP files with structured naming (`project-version-stage.zip`)
- Sets appropriate file permissions
- Updates modification timestamps for release management

## Technical Implementation

### HTML Processing Pipeline

The repository implements a sophisticated HTML processing pipeline that:

1. **Preserves Original Styling**: Maintains existing CSS links (such as OASIS CSS) while adding targeted improvements
2. **Enhanced Code Formatting**: Applies monospace fonts specifically to code elements without affecting document typography
3. **Link Preservation**: Ensures internal anchors and table-of-contents links remain functional
4. **Professional Layout**: Configures proper page margins, headers, and footers for PDF output

### Key Technologies

- **Python 3.x**: Core processing scripts
- **Pandoc**: Markdown to HTML conversion
- **wkhtmltopdf**: HTML to PDF rendering with JavaScript support
- **BeautifulSoup4**: HTML parsing and manipulation
- **Prettier**: Markdown formatting
- **GitHub Actions**: Automated workflow execution

### Dependencies

Python packages (see `requirements_pdf.txt`):
- `beautifulsoup4>=4.11.1` - HTML parsing and manipulation

System dependencies:
- `pandoc` - Document conversion
- `wkhtmltopdf` - PDF generation (installed via workflow)
- `prettier` - Markdown formatting

## Usage

### Running Workflows

1. **Format and Convert to HTML**:
   - Navigate to Actions → "1.0 - Convert Markdown -> HTML"
   - Provide the directory path (e.g., `csaf/v2.1/csd01`)
   - Set the modification date

2. **Generate PDF**:
   - Navigate to Actions → "2.0 - Convert HTML -> PDF"
   - Provide the same directory path
   - Confirm the modification date

3. **Create Distribution Package**:
   - Navigate to Actions → "3.0 - ZIP Package Files in Directory"
   - Provide the directory path for packaging
   - Set the release timestamp

### Manual Processing

For local development, the processing scripts can be run directly:

```bash
# HTML preprocessing for PDF optimization
python3 .github/src/fix_html_for_pdf.py input.html -o output_fixed.html

# PDF conversion
python3 .github/src/step_2_convert_html_to_pdf.py input.html -o output.pdf
```

## Development Guidelines

### Code Style
- Python code follows PEP-8 standards
- Shell scripts use proper error handling with `set -e`
- Professional documentation and logging throughout
- Type hints and comprehensive docstrings for Python functions

### Workflow Design
- Each workflow is atomic and handles specific processing stages
- Robust error handling and validation at each step
- Comprehensive logging for debugging and monitoring
- Automatic metadata management and timestamping

### Quality Assurance
- Validates input parameters before processing
- Comprehensive error reporting and debugging information
- Maintains file permissions and metadata consistency
- Automated testing through workflow execution

## Contributing

When contributing to this repository:

1. Maintain existing code style and conventions
2. Test workflows thoroughly before submitting
3. Update documentation for any functional changes
4. Ensure backward compatibility with existing documents
5. Follow OASIS documentation standards

## License

This repository is maintained by OASIS Open and follows OASIS intellectual property policies. See individual specification directories for specific licensing information.

---

**Repository maintained by**: OASIS Open  
**Contact**: Technical Committee administrators  
**Documentation**: See individual specification folders for detailed technical documentation
