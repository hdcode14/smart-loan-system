import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, session
from database import db
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

def generate_loan_agreement(loan_id):
    """Generate PDF loan agreement with penalty terms - MySQL Version"""
    try:
        # Get loan data from MySQL
        loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
        if not loan:
            return None
            
        # Get user data
        user = db.fetch_one("SELECT * FROM users WHERE UserID = %s", (loan['UserID'],))
        if not user:
            return None
            
        # Get borrower data for PAN number
        borrower = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (loan['UserID'],))
        
        # Create agreements directory if not exists
        os.makedirs('static/agreements', exist_ok=True)
        
        # Create PDF
        filename = f"loan_agreement_{loan_id}.pdf"
        filepath = os.path.join('static', 'agreements', filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title with professional styling
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,
            textColor=colors.HexColor('#1e40af'),
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("LOAN AGREEMENT", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Agreement Number
        applied_date = loan['AppliedDate']
        if isinstance(applied_date, str):
            applied_date = datetime.strptime(applied_date, '%Y-%m-%d %H:%M:%S')
            
        story.append(Paragraph(f"<b>Agreement No:</b> LA{loan_id:06d}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {applied_date.strftime('%d %B, %Y')}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Loan Details Table with enhanced styling
        emi_amount = loan['EMIAmount'] if loan['EMIAmount'] else 0
        total_repayable = emi_amount * loan['Duration']
        
        loan_data = [
            ['Borrower Information', ''],
            ['Full Name:', user['Name']],
            ['Email:', user['Email']],
            ['Phone:', user['Phone'] or 'Not provided'],
            ['Address:', user['Address'] or 'Not provided'],
            ['', ''],
            ['Loan Details', ''],
            ['Loan Amount:', f'₹{float(loan["Amount"]):,.2f}'],
            ['Interest Rate:', f'{float(loan["InterestRate"])}% per annum'],
            ['Loan Tenure:', f'{loan["Duration"]} months'],
            ['EMI Amount:', f'₹{float(emi_amount):,.2f}'],
            ['Total Repayable:', f'₹{float(total_repayable):,.2f}'],
            ['Loan Type:', loan['LoanType'].title()],
            ['Purpose:', loan['Purpose'] or 'Not specified']
        ]
        
        loan_table = Table(loan_data, colWidths=[2.5*inch, 4*inch])
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#1e3a8a')),
            ('BACKGROUND', (0, 6), (1, 6), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (0, 6), (1, 6), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 6), (1, 6), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, 5), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (0, 7), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        story.append(loan_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Terms and Conditions with Penalty Clause
        story.append(Paragraph("Terms and Conditions", styles['Heading2']))
        story.append(Spacer(1, 0.15*inch))
        
        terms = [
            "1. <b>Repayment Schedule:</b> The Borrower agrees to repay the loan in equated monthly installments (EMIs) as per the schedule provided.",
            "2. <b>Late Payment Penalties:</b> Late payments will attract a penalty of 2% per month on the overdue amount. The penalty will be calculated daily from the due date until the payment is made.",
            "3. <b>Penalty Calculation:</b> The daily penalty rate is calculated as (2% of EMI amount) ÷ 30 days. The total penalty accumulates daily until the overdue amount is paid in full.",
            "4. <b>Payment Priority:</b> In case of late payments, amounts received will first be applied towards penalties and then towards the EMI principal and interest.",
            "5. <b>Credit Impact:</b> Late payments may negatively impact the Borrower's credit score and future loan eligibility.",
            "6. <b>Pre-closure:</b> The loan can be pre-closed after 6 months with applicable pre-payment charges of 2% on the outstanding principal.",
            "7. <b>Default Consequences:</b> The Lender reserves the right to take legal action, engage collection agencies, and report to credit bureaus in case of persistent default.",
            "8. <b>Communication:</b> All communication regarding payments, penalties, and account status will be sent to the registered email and phone number.",
            "9. <b>Dispute Resolution:</b> All disputes are subject to the exclusive jurisdiction of courts in the location where this agreement is executed.",
            "10. <b>Agreement Changes:</b> Any changes to this agreement must be made in writing and signed by both parties."
        ]
        
        for term in terms:
            story.append(Paragraph(term, styles['Normal']))
            story.append(Spacer(1, 0.08*inch))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Penalty Calculation Example
        penalty_section_style = ParagraphStyle(
            'PenaltySection',
            parent=styles['Normal'],
            fontSize=10,
            backColor=colors.HexColor('#fff7ed'),
            borderPadding=10,
            borderColor=colors.HexColor('#fdba74'),
            borderWidth=1
        )
        
        penalty_example = f"""
        <b>Late Payment Penalty Example:</b><br/>
        For an EMI of ₹{float(emi_amount):,.2f}, the monthly penalty would be ₹{float(emi_amount) * 0.02:,.2f} (2%).<br/>
        Daily penalty: ₹{(float(emi_amount) * 0.02) / 30:,.2f} per day.<br/>
        <i>Example: 15 days overdue = ₹{((float(emi_amount) * 0.02) / 30) * 15:,.2f} penalty + ₹{float(emi_amount):,.2f} EMI = ₹{float(emi_amount) + (((float(emi_amount) * 0.02) / 30) * 15):,.2f} total due.</i>
        """
        
        story.append(Paragraph(penalty_example, penalty_section_style))
        story.append(Spacer(1, 0.4*inch))
        
        # Signatures section with enhanced styling
        story.append(Paragraph("Signatures", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        # Get PAN number from borrower profile
        pan_number = borrower['PANNumber'] if borrower and borrower['PANNumber'] else 'Not provided'
        
        signature_data = [
            ['For Borrower:', 'For Lender:'],
            ['', ''],
            ['', ''],
            ['Signature: _________________', 'Signature: _________________'],
            ['', ''],
            ['Name: ' + user['Name'], 'Name: Loan Management System'],
            ['', ''],
            ['Date: _________________', 'Date: _________________'],
            ['', ''],
            ['PAN: ' + pan_number, 'Official Stamp:']
        ]
        
        signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LINEABOVE', (0, 3), (0, 3), 1, colors.black),
            ('LINEABOVE', (1, 3), (1, 3), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(signature_table)
        
        # Important Notice Section
        story.append(Spacer(1, 0.4*inch))
        
        notice_style = ParagraphStyle(
            'ImportantNotice',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#dc2626'),
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("IMPORTANT: Please make timely payments to avoid penalties and protect your credit score.", notice_style))
        
        # Build PDF
        doc.build(story)
        
        # Update loan record in MySQL
        db.execute_query(
            "UPDATE loans SET AgreementPDF = %s WHERE LoanID = %s",
            (filename, loan_id)
        )
        
        print(f"✓ Loan agreement generated successfully: {filename}")
        return filepath
        
    except Exception as e:
        print(f"✗ Error generating agreement: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None