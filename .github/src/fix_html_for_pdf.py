#!/usr/bin/env python3
"""
HTML Preprocessor for Enhanced PDF Code Block Formatting

This script preprocesses HTML files by embedding targeted CSS for monospace
code blocks that wkhtmltopdf will properly render. The preprocessor preserves
existing CSS stylesheets (such as OASIS CSS) while adding specific improvements
for code elements to ensure optimal PDF output quality.

Key Features:
- Preserves original CSS links and styling
- Adds targeted monospace fixes for code elements only
- Maintains document structure and anchor functionality
- Optimizes HTML structure for PDF conversion
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_perfect_code_css() -> str:
    """
    Generate targeted CSS for enhanced code block formatting.
    
    Returns CSS rules that specifically target code elements without overriding
    existing document stylesheets. This approach preserves original styling
    while ensuring proper monospace formatting for code blocks in PDF output.
    
    Returns:
        str: CSS string containing targeted code formatting rules
    """
    return """
    /* TARGETED MONOSPACE FIXES - PRESERVE ORIGINAL OASIS CSS */
    
    /* Code elements - monospace font only */
    code, pre, .sourceCode, .highlight, tt, kbd, samp {
        font-family: "Courier New", "Liberation Mono", "DejaVu Sans Mono", "Consolas", "Monaco", monospace !important;
        font-weight: normal !important;
        font-style: normal !important;
        letter-spacing: 0 !important;
        word-spacing: 0 !important;
        -webkit-font-feature-settings: normal !important;
        font-feature-settings: normal !important;
    }
    
    /* Inline code styling */
    code {
        font-size: 0.9em !important;
        background-color: #f5f5f5 !important;
        border: 1px solid #ddd !important;
        border-radius: 2px !important;
        padding: 1px 4px !important;
        white-space: nowrap !important;
    }
    
    /* Code blocks styling */
    pre {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        page-break-inside: auto !important;
    }
    
    pre code {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        white-space: pre-wrap !important;
        font-size: inherit !important;
    }
    
    /* Syntax highlighting blocks */
    .sourceCode, .highlight {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
    }
    
    /* Language-specific code blocks */
    .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        padding: 10px !important;
        white-space: pre-wrap !important;
    }
    
    /* Code in tables */
    table code, td code, th code {
        font-size: 0.8em !important;
        white-space: nowrap !important;
    }
    
    /* PDF-specific code formatting */
    @media print {
        code, pre, .sourceCode, .highlight {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        
        pre {
            page-break-inside: auto !important;
            orphans: 2 !important;
            widows: 2 !important;
        }
    }
    
    /* Page setup - portrait with wider margins */
    @page {
        size: A4 portrait;
        margin: 2.5cm 2cm 2.5cm 2cm;
    }
    """


def preprocess_html_for_pdf(html_file: Path, output_file: Path) -> None:
    """
    Preprocess HTML file by embedding targeted CSS for enhanced code block formatting.
    
    This function reads an HTML file, parses it, and adds targeted CSS rules
    for code elements while preserving existing stylesheets and document structure.
    The resulting HTML is optimized for PDF conversion with proper code formatting.
    
    Args:
        html_file (Path): Path to the input HTML file
        output_file (Path): Path where the preprocessed HTML will be saved
        
    Raises:
        IOError: If file reading or writing fails
    """
    logger.info(f"Preprocessing HTML: {html_file} -> {output_file}")
    
    # Read the HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Ensure document has a proper head section
    if not soup.head:
        head = soup.new_tag('head')
        if soup.html:
            soup.html.insert(0, head)
        else:
            soup.insert(0, head)
    
    # Add targeted CSS for code formatting
    # Note: Appending rather than prepending to preserve existing CSS precedence
    style_tag = soup.new_tag('style')
    style_tag.string = get_perfect_code_css()
    soup.head.append(style_tag)
    
    # Ensure proper CSS classes for code block elements
    for pre in soup.find_all('pre'):
        if not pre.get('class'):
            pre['class'] = ['code-block']
    
    # Add CSS classes to inline code elements
    for code in soup.find_all('code'):
        if code.parent and code.parent.name != 'pre':
            if not code.get('class'):
                code['class'] = ['inline-code']
    
    # Write preprocessed HTML to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    logger.info(f"HTML preprocessing completed successfully: {output_file}")


def main():
    """Command-line interface for HTML preprocessing."""
    parser = argparse.ArgumentParser(
        description="Preprocess HTML for enhanced PDF code block formatting",
        epilog="This tool adds targeted monospace CSS while preserving existing styles and document structure."
    )
    
    parser.add_argument(
        "html_file",
        help="Input HTML file to preprocess"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output HTML file (default: same as input with _fixed suffix)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging based on verbosity level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Determine output file path
    input_path = Path(args.html_file)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_stem(input_path.stem + "_fixed")
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    try:
        preprocess_html_for_pdf(input_path, output_path)
        print("HTML preprocessing completed successfully")
        print(f"Output: {output_path}")
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        print(f"HTML preprocessing failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
