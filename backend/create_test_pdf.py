"""
Test PDF Generator — creates a realistic multi-document PDF for testing.

Generates a PDF containing multiple document types:
- A cover letter
- 2 bank statements (different months) with tables
- A tax form (Form 1040-like)
- An invoice with a table
- A generic report

This is used ONLY for testing. The pipeline is generic and handles any PDF.
"""
import sys
sys.path.insert(0, ".")

import pymupdf
from pathlib import Path


def create_test_pdf(output_path: str = "test_documents/sample_loan_file.pdf"):
    """Create a multi-document test PDF with various document types."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()

    # --- Document 1: Cover Letter (1 page) ---
    page = doc.new_page(width=612, height=792)
    _add_text(page, "ACME Mortgage Corporation", 72, 80, size=18, bold=True)
    _add_text(page, "123 Finance Street, Suite 400", 72, 110, size=10)
    _add_text(page, "New York, NY 10001", 72, 125, size=10)
    _add_line(page, 72, 150, 540, 150)
    _add_text(page, "Loan Application Package", 72, 180, size=16, bold=True)
    _add_text(page, "Date: January 15, 2026", 72, 210, size=11)
    _add_text(page, "Applicant: John Smith", 72, 230, size=11)
    _add_text(page, "Loan Number: LN-2026-00142", 72, 250, size=11)
    _add_text(page, "Dear Underwriting Team,", 72, 290, size=11)
    body = (
        "Please find enclosed the complete loan application package for the above-referenced "
        "borrower. This package contains all required documentation including bank statements, "
        "tax returns, income verification, and property-related documents. All documents have "
        "been verified for completeness and accuracy."
    )
    _add_wrapped_text(page, body, 72, 320, 468, size=11, line_height=16)
    _add_text(page, "Sincerely,", 72, 440, size=11)
    _add_text(page, "Jane Rodriguez", 72, 470, size=11, bold=True)
    _add_text(page, "Loan Officer", 72, 488, size=11)
    _add_text(page, "Page 1 of 1", 280, 750, size=9)

    # --- Document 2: Bank Statement - January 2026 (3 pages) ---
    # Page 1
    page = doc.new_page(width=612, height=792)
    _add_text(page, "FIRST NATIONAL BANK", 72, 60, size=16, bold=True)
    _add_text(page, "Account Statement", 72, 85, size=13, bold=True)
    _add_line(page, 72, 100, 540, 100)
    _add_text(page, "Account Holder: John Smith", 72, 120, size=10)
    _add_text(page, "Account Number: ****4521", 72, 135, size=10)
    _add_text(page, "Statement Period: January 1, 2026 - January 31, 2026", 72, 150, size=10)
    _add_text(page, "Account Type: Checking", 72, 165, size=10)
    _add_line(page, 72, 185, 540, 185)
    _add_text(page, "Account Summary", 72, 205, size=12, bold=True)
    # Summary table
    _draw_table(page, 72, 225, [
        ["Beginning Balance", "$4,250.00"],
        ["Total Deposits", "$7,850.00"],
        ["Total Withdrawals", "$5,430.22"],
        ["Ending Balance", "$6,669.78"],
    ], col_widths=[250, 150])
    # Transaction table header
    _add_text(page, "Transaction Detail", 72, 370, size=12, bold=True)
    _draw_table(page, 72, 390, [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["01/02", "Direct Deposit - Employer", "", "$3,500.00", "$7,750.00"],
        ["01/03", "Electric Company", "$125.50", "", "$7,624.50"],
        ["01/05", "Grocery Store #442", "$87.23", "", "$7,537.27"],
        ["01/07", "Gas Station", "$45.00", "", "$7,492.27"],
        ["01/08", "Online Transfer In", "", "$350.00", "$7,842.27"],
        ["01/10", "Rent Payment", "$1,800.00", "", "$6,042.27"],
        ["01/12", "Restaurant", "$52.30", "", "$5,989.97"],
        ["01/14", "Insurance Premium", "$220.00", "", "$5,769.97"],
    ], col_widths=[60, 180, 70, 70, 80], header=True)
    _add_text(page, "Page 1 of 3", 280, 750, size=9)

    # Page 2 (continuation)
    page = doc.new_page(width=612, height=792)
    _add_text(page, "FIRST NATIONAL BANK", 72, 60, size=14, bold=True)
    _add_text(page, "Account: ****4521   Statement Period: January 2026", 72, 80, size=9)
    _add_line(page, 72, 95, 540, 95)
    _add_text(page, "Transaction Detail (continued)", 72, 115, size=12, bold=True)
    _draw_table(page, 72, 135, [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["01/15", "Direct Deposit - Employer", "", "$3,500.00", "$9,269.97"],
        ["01/16", "Phone Bill", "$95.00", "", "$9,174.97"],
        ["01/17", "Amazon Purchase", "$124.99", "", "$9,049.98"],
        ["01/18", "ATM Withdrawal", "$200.00", "", "$8,849.98"],
        ["01/20", "Water Utility", "$45.20", "", "$8,804.78"],
        ["01/22", "Streaming Service", "$15.99", "", "$8,788.79"],
        ["01/23", "Gym Membership", "$49.99", "", "$8,738.80"],
        ["01/25", "Grocery Store #442", "$92.15", "", "$8,646.65"],
        ["01/27", "Car Payment", "$385.00", "", "$8,261.65"],
        ["01/28", "Credit Card Payment", "$500.00", "", "$7,761.65"],
        ["01/29", "Medical Co-pay", "$35.00", "", "$7,726.65"],
        ["01/30", "Online Purchase", "$156.87", "", "$7,569.78"],
        ["01/31", "Service Fee", "$5.00", "", "$7,564.78"],
    ], col_widths=[60, 180, 70, 70, 80], header=True)
    _add_text(page, "Page 2 of 3", 280, 750, size=9)

    # Page 3 (summary)
    page = doc.new_page(width=612, height=792)
    _add_text(page, "FIRST NATIONAL BANK", 72, 60, size=14, bold=True)
    _add_text(page, "Account: ****4521   Statement Period: January 2026", 72, 80, size=9)
    _add_line(page, 72, 95, 540, 95)
    _add_text(page, "Monthly Summary", 72, 120, size=12, bold=True)
    _draw_table(page, 72, 140, [
        ["Category", "Amount"],
        ["Housing", "$1,800.00"],
        ["Utilities", "$265.70"],
        ["Food & Dining", "$231.68"],
        ["Transportation", "$430.00"],
        ["Insurance", "$220.00"],
        ["Entertainment", "$65.98"],
        ["Shopping", "$281.86"],
        ["Medical", "$35.00"],
        ["Fees", "$5.00"],
        ["Total Expenses", "$5,335.22"],
    ], col_widths=[250, 150], header=True)
    _add_text(page, "Average Daily Balance: $7,215.43", 72, 420, size=10)
    _add_text(page, "This statement is a true and accurate record of your account activity.", 72, 450, size=9)
    _add_text(page, "Page 3 of 3", 280, 750, size=9)

    # --- Document 3: Bank Statement - February 2026 (2 pages) ---
    page = doc.new_page(width=612, height=792)
    _add_text(page, "FIRST NATIONAL BANK", 72, 60, size=16, bold=True)
    _add_text(page, "Account Statement", 72, 85, size=13, bold=True)
    _add_line(page, 72, 100, 540, 100)
    _add_text(page, "Account Holder: John Smith", 72, 120, size=10)
    _add_text(page, "Account Number: ****4521", 72, 135, size=10)
    _add_text(page, "Statement Period: February 1, 2026 - February 28, 2026", 72, 150, size=10)
    _add_text(page, "Account Type: Checking", 72, 165, size=10)
    _add_line(page, 72, 185, 540, 185)
    _add_text(page, "Account Summary", 72, 205, size=12, bold=True)
    _draw_table(page, 72, 225, [
        ["Beginning Balance", "$7,564.78"],
        ["Total Deposits", "$7,150.00"],
        ["Total Withdrawals", "$5,890.45"],
        ["Ending Balance", "$8,824.33"],
    ], col_widths=[250, 150])
    _add_text(page, "Transaction Detail", 72, 370, size=12, bold=True)
    _draw_table(page, 72, 390, [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["02/01", "Direct Deposit - Employer", "", "$3,500.00", "$11,064.78"],
        ["02/03", "Rent Payment", "$1,800.00", "", "$9,264.78"],
        ["02/04", "Electric Company", "$138.20", "", "$9,126.58"],
        ["02/06", "Grocery Store", "$95.40", "", "$9,031.18"],
        ["02/08", "Gas Station", "$52.00", "", "$8,979.18"],
        ["02/10", "Online Transfer In", "", "$150.00", "$9,129.18"],
        ["02/12", "Insurance Premium", "$220.00", "", "$8,909.18"],
    ], col_widths=[60, 180, 70, 70, 80], header=True)
    _add_text(page, "Page 1 of 2", 280, 750, size=9)

    page = doc.new_page(width=612, height=792)
    _add_text(page, "FIRST NATIONAL BANK", 72, 60, size=14, bold=True)
    _add_text(page, "Account: ****4521   Statement Period: February 2026", 72, 80, size=9)
    _add_line(page, 72, 95, 540, 95)
    _draw_table(page, 72, 115, [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["02/14", "Restaurant - Valentine's", "$85.00", "", "$8,824.18"],
        ["02/15", "Direct Deposit - Employer", "", "$3,500.00", "$12,324.18"],
        ["02/17", "Phone Bill", "$95.00", "", "$12,229.18"],
        ["02/19", "Amazon Purchase", "$67.50", "", "$12,161.68"],
        ["02/20", "ATM Withdrawal", "$300.00", "", "$11,861.68"],
        ["02/22", "Gym Membership", "$49.99", "", "$11,811.69"],
        ["02/25", "Car Payment", "$385.00", "", "$11,426.69"],
        ["02/26", "Credit Card Payment", "$600.00", "", "$10,826.69"],
        ["02/27", "Grocery Store", "$102.36", "", "$10,724.33"],
        ["02/28", "Streaming Services", "$15.99", "", "$10,708.34"],
    ], col_widths=[60, 180, 70, 70, 80], header=True)
    _add_text(page, "Average Daily Balance: $9,845.21", 72, 420, size=10)
    _add_text(page, "Page 2 of 2", 280, 750, size=9)

    # --- Document 4: Tax Return Form 1040 (2 pages) ---
    page = doc.new_page(width=612, height=792)
    _add_text(page, "Department of the Treasury — Internal Revenue Service", 72, 50, size=9)
    _add_text(page, "Form 1040", 72, 75, size=20, bold=True)
    _add_text(page, "U.S. Individual Income Tax Return", 200, 80, size=12)
    _add_text(page, "Tax Year 2025", 450, 75, size=11, bold=True)
    _add_line(page, 72, 100, 540, 100)
    _add_text(page, "Filing Status: Married Filing Jointly", 72, 120, size=10)
    _add_text(page, "Name: John Smith", 72, 140, size=10)
    _add_text(page, "SSN: XXX-XX-4521", 400, 140, size=10)
    _add_text(page, "Spouse: Mary Smith", 72, 160, size=10)
    _add_text(page, "SSN: XXX-XX-8832", 400, 160, size=10)
    _add_text(page, "Address: 456 Oak Avenue, Springfield, IL 62701", 72, 180, size=10)
    _add_line(page, 72, 200, 540, 200)
    _add_text(page, "Income", 72, 220, size=12, bold=True)
    _draw_table(page, 72, 240, [
        ["Line", "Description", "Amount"],
        ["1a", "Wages, salaries, tips (W-2)", "$84,000.00"],
        ["2b", "Taxable interest", "$1,245.00"],
        ["3b", "Ordinary dividends", "$890.00"],
        ["4b", "IRA distributions (taxable)", "$0.00"],
        ["7", "Capital gain or loss", "$2,150.00"],
        ["8", "Other income", "$500.00"],
        ["9", "Total income", "$88,785.00"],
    ], col_widths=[40, 280, 120], header=True)
    _add_text(page, "Adjustments to Income", 72, 450, size=12, bold=True)
    _draw_table(page, 72, 470, [
        ["Line", "Description", "Amount"],
        ["11", "Educator expenses", "$300.00"],
        ["13", "IRA deduction", "$6,500.00"],
        ["15", "Student loan interest", "$2,500.00"],
        ["", "Total adjustments", "$9,300.00"],
        ["", "Adjusted Gross Income", "$79,485.00"],
    ], col_widths=[40, 280, 120], header=True)
    _add_text(page, "Page 1 of 2", 280, 750, size=9)

    page = doc.new_page(width=612, height=792)
    _add_text(page, "Form 1040 (2025)", 72, 50, size=10)
    _add_text(page, "John & Mary Smith", 300, 50, size=10)
    _add_text(page, "SSN: XXX-XX-4521", 450, 50, size=10)
    _add_line(page, 72, 70, 540, 70)
    _add_text(page, "Tax and Credits", 72, 90, size=12, bold=True)
    _draw_table(page, 72, 110, [
        ["Line", "Description", "Amount"],
        ["12", "Standard deduction", "$29,200.00"],
        ["14", "Taxable income", "$50,285.00"],
        ["16", "Tax", "$5,618.00"],
        ["19", "Child tax credit", "$2,000.00"],
        ["22", "Other credits", "$0.00"],
        ["24", "Total tax", "$3,618.00"],
    ], col_widths=[40, 280, 120], header=True)
    _add_text(page, "Payments", 72, 280, size=12, bold=True)
    _draw_table(page, 72, 300, [
        ["Line", "Description", "Amount"],
        ["25a", "Federal tax withheld (W-2)", "$8,400.00"],
        ["26", "Estimated tax payments", "$0.00"],
        ["33", "Total payments", "$8,400.00"],
    ], col_widths=[40, 280, 120], header=True)
    _add_text(page, "Refund", 72, 410, size=12, bold=True)
    _add_text(page, "35a. Amount overpaid: $4,782.00", 72, 435, size=11)
    _add_text(page, "36.  Refund amount:   $4,782.00", 72, 455, size=11)
    _add_text(page, "Page 2 of 2", 280, 750, size=9)

    # --- Document 5: Invoice (1 page) ---
    page = doc.new_page(width=612, height=792)
    _add_text(page, "INVOICE", 250, 60, size=22, bold=True)
    _add_line(page, 72, 90, 540, 90)
    _add_text(page, "Springfield Home Inspections, LLC", 72, 110, size=12, bold=True)
    _add_text(page, "789 Main Street, Springfield, IL 62701", 72, 128, size=10)
    _add_text(page, "Phone: (217) 555-0198", 72, 143, size=10)
    _add_text(page, "Invoice No: INV-2026-0087", 400, 110, size=10)
    _add_text(page, "Date: January 10, 2026", 400, 128, size=10)
    _add_text(page, "Due Date: February 10, 2026", 400, 143, size=10)
    _add_line(page, 72, 165, 540, 165)
    _add_text(page, "Bill To:", 72, 185, size=10, bold=True)
    _add_text(page, "John Smith", 72, 200, size=10)
    _add_text(page, "456 Oak Avenue", 72, 215, size=10)
    _add_text(page, "Springfield, IL 62701", 72, 230, size=10)
    _add_line(page, 72, 250, 540, 250)
    _draw_table(page, 72, 270, [
        ["Item", "Description", "Qty", "Rate", "Amount"],
        ["1", "Home Inspection - Standard", "1", "$450.00", "$450.00"],
        ["2", "Radon Testing", "1", "$150.00", "$150.00"],
        ["3", "Termite Inspection", "1", "$85.00", "$85.00"],
        ["4", "Mold Assessment", "1", "$200.00", "$200.00"],
        ["", "", "", "Subtotal", "$885.00"],
        ["", "", "", "Tax (6.25%)", "$55.31"],
        ["", "", "", "Total Due", "$940.31"],
    ], col_widths=[40, 200, 40, 80, 80], header=True)
    _add_text(page, "Payment Terms: Net 30 days", 72, 520, size=10)
    _add_text(page, "Thank you for your business!", 72, 545, size=10)

    # --- Document 6: Appraisal Summary Report (2 pages) ---
    page = doc.new_page(width=612, height=792)
    _add_text(page, "UNIFORM RESIDENTIAL APPRAISAL REPORT", 120, 55, size=14, bold=True)
    _add_line(page, 72, 75, 540, 75)
    _add_text(page, "Subject Property", 72, 95, size=12, bold=True)
    _draw_table(page, 72, 115, [
        ["Field", "Value"],
        ["Property Address", "456 Oak Avenue, Springfield, IL 62701"],
        ["Legal Description", "Lot 12, Block 3, Oak Park Subdivision"],
        ["County", "Sangamon"],
        ["Tax Year", "2025"],
        ["R.E. Taxes", "$4,200.00"],
        ["Neighborhood", "Suburban"],
        ["Property Type", "Single Family Residence"],
        ["Year Built", "1998"],
        ["Living Area (sq ft)", "2,150"],
        ["Lot Size", "0.35 acres"],
    ], col_widths=[150, 300], header=True)
    _add_text(page, "Comparable Sales", 72, 380, size=12, bold=True)
    _draw_table(page, 72, 400, [
        ["", "Subject", "Comparable 1", "Comparable 2", "Comparable 3"],
        ["Address", "456 Oak Ave", "123 Elm St", "789 Pine Rd", "321 Maple Dr"],
        ["Sale Price", "—", "$285,000", "$298,000", "$275,000"],
        ["Date of Sale", "—", "10/2025", "11/2025", "09/2025"],
        ["Sq. Footage", "2,150", "2,100", "2,250", "2,000"],
        ["Bedrooms", "4", "3", "4", "3"],
        ["Bathrooms", "2.5", "2", "2.5", "2"],
        ["Garage", "2-car", "2-car", "2-car", "1-car"],
        ["Adjustment", "—", "+$5,000", "-$3,000", "+$12,000"],
        ["Adj. Price", "—", "$290,000", "$295,000", "$287,000"],
    ], col_widths=[70, 90, 95, 95, 95], header=True)
    _add_text(page, "Page 1 of 2", 280, 750, size=9)

    page = doc.new_page(width=612, height=792)
    _add_text(page, "APPRAISAL REPORT (continued)", 72, 55, size=12, bold=True)
    _add_text(page, "Property: 456 Oak Avenue, Springfield, IL", 72, 75, size=10)
    _add_line(page, 72, 90, 540, 90)
    _add_text(page, "Reconciliation", 72, 115, size=12, bold=True)
    body2 = (
        "Based on the analysis of comparable sales, market conditions, and property "
        "characteristics, the appraised value of the subject property is determined to be "
        "$290,000. The sales comparison approach was given the most weight in the final "
        "value conclusion. The comparable sales were selected from the same neighborhood "
        "and adjusted for differences in size, condition, and features."
    )
    _add_wrapped_text(page, body2, 72, 140, 468, size=11, line_height=16)
    _add_text(page, "Appraised Value: $290,000", 72, 260, size=14, bold=True)
    _add_line(page, 72, 290, 540, 290)
    _add_text(page, "Certification", 72, 310, size=12, bold=True)
    _add_text(page, "I certify that the statements of fact contained in this report are true", 72, 335, size=10)
    _add_text(page, "and correct to the best of my knowledge and belief.", 72, 350, size=10)
    _add_text(page, "Appraiser: Robert Johnson, MAI", 72, 390, size=11, bold=True)
    _add_text(page, "License #: IL-553-001234", 72, 410, size=10)
    _add_text(page, "Date: January 8, 2026", 72, 428, size=10)
    _add_text(page, "Page 2 of 2", 280, 750, size=9)

    # Save the document
    doc.save(output_path)
    doc.close()
    print(f"Created test PDF: {output_path} ({doc.page_count if hasattr(doc, 'page_count') else 'N/A'} pages)")
    return output_path


# --- Helper functions for PDF generation ---

def _add_text(page, text, x, y, size=11, bold=False, color=(0, 0, 0)):
    font = "helv" if not bold else "hebo"
    try:
        page.insert_text(
            pymupdf.Point(x, y),
            text,
            fontsize=size,
            fontname=font,
            color=color,
        )
    except Exception:
        page.insert_text(
            pymupdf.Point(x, y),
            text,
            fontsize=size,
            fontname="helv",
            color=color,
        )


def _add_wrapped_text(page, text, x, y, max_width, size=11, line_height=16):
    words = text.split()
    line = ""
    current_y = y
    chars_per_line = int(max_width / (size * 0.5))

    for word in words:
        test_line = f"{line} {word}".strip()
        if len(test_line) > chars_per_line:
            _add_text(page, line, x, current_y, size=size)
            line = word
            current_y += line_height
        else:
            line = test_line

    if line:
        _add_text(page, line, x, current_y, size=size)


def _add_line(page, x1, y1, x2, y2, color=(0.3, 0.3, 0.3), width=1):
    shape = page.new_shape()
    shape.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2))
    shape.finish(color=color, width=width)
    shape.commit()


def _draw_table(page, x, y, data, col_widths, header=False):
    """Draw a simple table on the page."""
    row_height = 18
    current_y = y

    for row_idx, row in enumerate(data):
        current_x = x
        is_header_row = header and row_idx == 0

        # Draw cell borders
        for col_idx, cell in enumerate(row):
            w = col_widths[col_idx] if col_idx < len(col_widths) else 80

            # Draw cell rectangle
            rect = pymupdf.Rect(current_x, current_y, current_x + w, current_y + row_height)
            shape = page.new_shape()
            shape.draw_rect(rect)

            if is_header_row:
                shape.finish(color=(0.3, 0.3, 0.3), fill=(0.9, 0.9, 0.9), width=0.5)
            else:
                shape.finish(color=(0.7, 0.7, 0.7), width=0.3)
            shape.commit()

            # Add text
            text = str(cell) if cell else ""
            text_size = 8 if is_header_row else 8
            _add_text(
                page, text[:35],  # Truncate long text
                current_x + 3, current_y + 13,
                size=text_size,
                bold=is_header_row,
            )

            current_x += w
        current_y += row_height


if __name__ == "__main__":
    path = create_test_pdf()
    print(f"Test PDF created at: {path}")
