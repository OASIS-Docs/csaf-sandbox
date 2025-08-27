import unittest
from unittest.mock import patch, mock_open, MagicMock

class TestPDFGenerator(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data="**[JADN-v1.0]**\n_Specification for JSON Abstract Data Notation Version 1.0_. Edited by David Kemp. 21 October 2020.")
    @patch('subprocess.run')
    def test_generate_pdf(self, mock_subprocess_run, mock_file):
        logger = MagicMock()
        pdf_generator = PDFGenerator('dummy.html', 'dummy.pdf', 'dummy.md', logger)

        pdf_generator.generate_pdf()
        
        expected_date = '21 October 2020'
        expected_year = '2020'

        cli_command = [
            'wkhtmltopdf', '--page-size', 'Letter', 
            '-T', '25', '-B', '20', '--header-spacing', '6', 
            '--header-font-size', '10', '--header-center', 'Standards Track Work Product', 
            '--footer-line', '--footer-spacing', '4', '--footer-left', 'dummy.html', 
            '--footer-center', f'Copyright © OASIS Open {expected_year}. All Rights Reserved.', 
            '--footer-right', f'{expected_date}  - Page [page] of [topage]', 
            '--footer-font-size', '8', '--footer-font-name', 'LiberationSans', '--no-outline', 
            'dummy.html', 'dummy.pdf'
        ]

        logger.log_info.assert_any_call(f'Generating PDF with command: {" ".join(cli_command)}')
        mock_subprocess_run.assert_called_once_with(cli_command, check=True)
        logger.log_info.assert_any_call('PDF generated successfully: dummy.pdf')