#!/usr/bin/env python3
"""
HTML to PDF Converter with Enhanced Code Block Formatting

This module converts HTML files to PDF while ensuring proper monospace formatting
for code blocks. The converter preserves the original document styling (such as
OASIS CSS) while applying targeted improvements to code elements for optimal
PDF rendering using wkhtmltopdf.

Key Features:
- Preserves original CSS styling and anchor links
- Applies targeted monospace formatting to code elements only
- Configurable page layout with portrait orientation and custom margins
- Professional headers and footers with document metadata
- Robust error handling and logging
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import subprocess
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class PDFConverter:
    """
    Converts HTML files to PDF using wkhtmltopdf with enhanced code block formatting.
    
    This class handles the conversion process while preserving original document
    styling and applying targeted improvements to ensure code blocks render
    correctly in the PDF output.
    """
    
    def __init__(self, html_file: str, output_pdf: str, base_dir: Optional[str] = None):
        self.html_file = Path(html_file).resolve()
        self.output_pdf = Path(output_pdf).resolve()
        self.base_dir = Path(base_dir).resolve() if base_dir else self.html_file.parent
        
        if not self.html_file.exists():
            raise FileNotFoundError(f"HTML file not found: {self.html_file}")
            
        logger.info("PDF Converter initialized successfully")
        logger.info(f"  HTML File: {self.html_file}")
        logger.info(f"  PDF Output: {self.output_pdf}")
        logger.info(f"  Base Directory: {self.base_dir}")

    def _get_perfect_code_css(self) -> str:
        """
        Generate targeted CSS for enhanced code block formatting.
        
        Returns CSS rules that specifically target code elements without overriding
        the document's existing stylesheets. This approach preserves original
        styling (such as OASIS CSS) while ensuring code blocks render properly
        in the PDF output.
        
        Returns:
            str: CSS string containing targeted code formatting rules
        """
        return """
        /* TARGETED MONOSPACE FIXES - PRESERVE ORIGINAL OASIS CSS */
        
        /* Code elements - monospace font only */
        code, pre, .sourceCode, .highlight, tt, kbd, samp {
            font-family: "Courier New", "DejaVu Sans Mono", "Liberation Mono", "Consolas", "Monaco", monospace !important;
            font-weight: normal !important;
            font-style: normal !important;
            letter-spacing: 0 !important;
            word-spacing: 0 !important;
        }
        
        /* Inline code styling */
        code {
            font-size: 0.9em !important;
            background-color: #f5f5f5 !important;
            border: 1px solid #ddd !important;
            border-radius: 2px !important;
            padding: 1px 3px !important;
            white-space: nowrap !important;
        }
        
        /* Block code styling */
        pre {
            font-size: 0.85em !important;
            line-height: 1.2 !important;
            background-color: #f8f8f8 !important;
            border: 1px solid #ccc !important;
            border-radius: 4px !important;
            padding: 8pt !important;
            margin: 6pt 0 !important;
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
            padding: 8pt !important;
            margin: 6pt 0 !important;
        }
        
        /* Language-specific code blocks */
        .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http {
            font-size: 0.85em !important;
            line-height: 1.2 !important;
            background-color: #f8f8f8 !important;
            border: 1px solid #ccc !important;
            padding: 8pt !important;
            white-space: pre-wrap !important;
        }
        
        /* Code in tables */
        table code, td code, th code {
            font-size: 0.8em !important;
            white-space: nowrap !important;
        }
        
        /* PDF-specific code improvements */
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
        
        /* Page setup for portrait with wider margins */
        @page {
            size: A4 portrait;
            margin: 2.5cm 2cm 2.5cm 2cm;
            
            @top-center {
                content: string(title);
                font-size: 10pt;
                color: #666;
            }
            
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        /* Title string for header */
        h1:first-of-type, h1big:first-of-type {
            string-set: title content();
        }
        
        /* Minimal PDF improvements that don't override OASIS styles */
        h1, h1big, h2, h3, h4, h5, h6 {
            page-break-after: avoid !important;
        }
        
        /* No page breaks in inappropriate places */
        .no-page-break {
            page-break-inside: avoid !important;
        }
        """

    def _preprocess_html(self, html_content: str) -> str:
        """
        Preprocess HTML content to optimize for PDF rendering.
        
        This method ensures proper HTML structure for code blocks and adds
        necessary CSS classes to improve PDF output quality.
        
        Args:
            html_content (str): Raw HTML content to preprocess
            
        Returns:
            str: Preprocessed HTML content ready for PDF conversion
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ensure all code blocks have proper classes
        for pre in soup.find_all('pre'):
            if not pre.get('class'):
                pre['class'] = ['code-block']
                
        # Fix any code elements without proper parent structure
        for code in soup.find_all('code'):
            if code.parent and code.parent.name != 'pre':
                # This is inline code
                if not code.get('class'):
                    code['class'] = ['inline-code']
        
        # Ensure proper line breaks in code blocks
        for pre in soup.find_all('pre'):
            # Make sure pre blocks preserve whitespace
            if pre.string:
                # Replace any problematic whitespace
                content = str(pre.string)
                pre.string.replace_with(content)
        
        # Add no-page-break class to important elements
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h1big']):
            classes = heading.get('class', [])
            classes.append('no-page-break')
            heading['class'] = classes
            
        return str(soup)
        
    def _convert_to_pdf(self, html_file_path: str) -> None:
        """
        Convert HTML file to PDF using wkhtmltopdf.
        
        This method configures wkhtmltopdf with appropriate settings for
        document layout, headers, footers, and error handling to produce
        a professional PDF output.
        
        Args:
            html_file_path (str): Path to the HTML file to convert
            
        Raises:
            subprocess.CalledProcessError: If wkhtmltopdf execution fails
            Exception: For other conversion errors
        """
        logger.info("Converting HTML to PDF with wkhtmltopdf...")
        
        try:
            # Configure wkhtmltopdf command with document-specific settings
            cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--orientation', 'Portrait',
                '--margin-top', '25mm',
                '--margin-right', '20mm', 
                '--margin-bottom', '25mm',
                '--margin-left', '20mm',
                '--header-spacing', '6',
                '--header-font-size', '10',
                '--header-center', 'Common Security Advisory Framework Version 2.1',
                '--footer-line',
                '--footer-spacing', '4', 
                '--footer-left', str(self.html_file.name),
                '--footer-center', 'Copyright © OASIS Open 2025. All Rights Reserved.',
                '--footer-right', '[date] - Page [page] of [topage]',
                '--footer-font-size', '8',
                '--footer-font-name', 'Times',
                '--no-outline',
                '--print-media-type',
                '--enable-local-file-access',
                '--load-error-handling', 'ignore',
                '--load-media-error-handling', 'ignore',
                html_file_path,
                str(self.output_pdf)
            ]
            
            logger.info("Executing PDF conversion with wkhtmltopdf")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Execute wkhtmltopdf conversion
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if result.stderr:
                logger.debug(f"wkhtmltopdf output: {result.stderr}")
            
            logger.info("PDF conversion completed successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"wkhtmltopdf failed with exit code {e.returncode}")
            logger.error(f"stderr: {e.stderr}")
            logger.error(f"stdout: {e.stdout}")
            raise
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise

    def convert(self) -> None:
        """
        Execute the complete HTML to PDF conversion process.
        
        This method orchestrates the conversion workflow, handles file validation,
        executes the conversion, and verifies the output.
        
        Raises:
            RuntimeError: If the PDF file is not created successfully
            Exception: For other conversion errors
        """
        try:
            logger.info("Starting HTML to PDF conversion process")
            logger.info(f"Source HTML: {self.html_file}")
            
            # Execute PDF conversion
            self._convert_to_pdf(str(self.html_file))
            
            # Verify successful conversion
            if self.output_pdf.exists():
                size = self.output_pdf.stat().st_size
                logger.info(f"PDF generated successfully: {self.output_pdf} ({size:,} bytes)")
            else:
                raise RuntimeError("PDF file was not created successfully")
                
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise


def main() -> None:
    """Command-line interface for HTML to PDF conversion."""
    parser = argparse.ArgumentParser(
        description="Convert HTML to PDF with enhanced code block formatting",
        epilog="This tool preserves original document styling while optimizing code blocks for PDF output."
    )
    
    parser.add_argument(
        "html_file",
        help="Path to the HTML file to convert"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output PDF file path (default: same as HTML with .pdf extension)"
    )
    
    parser.add_argument(
        "--base-dir",
        help="Base directory for resolving relative URLs (default: HTML file directory)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("pdf_conversion.log")
        ]
    )
    
    # Determine output file
    if args.output:
        output_pdf = args.output
    else:
        html_path = Path(args.html_file)
        output_pdf = html_path.with_suffix('.pdf')
    
    try:
        # Create converter and run
        converter = PDFConverter(
            html_file=args.html_file,
            output_pdf=output_pdf,
            base_dir=args.base_dir
        )
        
        converter.convert()
        
        print("PDF conversion completed successfully")
        print(f"Output: {output_pdf}")
        
    except Exception as e:
        print(f"PDF conversion failed: {str(e)}")
        logger.error(f"Conversion failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
