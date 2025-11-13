from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, session
from database import db
from auth import Auth
from loan_services import LoanServices  # Only LoanServices from here
from wallet_services import WalletServices  # Import WalletServices from its own file
import json
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import functools

app = Flask(__name__)
app.config.from_object('config.Config')

# Login required decorator
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def create_default_admin():
    try:
        # Check if admin already exists
        admin = db.fetch_one("SELECT * FROM users WHERE UserType = 'admin'")
        if not admin:
            # Create admin user
            query = """
            INSERT INTO users (Name, Email, PasswordHash, UserType, Phone, Address) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            user_id = db.execute_query(query, (
                'System Administrator',
                'admin@smartloan.com',
                Auth.hash_password('admin123'),
                'admin',
                '+1-555-0001',
                '123 Admin Street, City, State'
            ))
            
            if user_id:
                # Create admin profile
                db.execute_query(
                    "INSERT INTO admins (UserID, Department, PermissionLevel, EmployeeID) VALUES (%s, %s, %s, %s)",
                    (user_id, 'Administration', 'super_admin', 'ADM001')
                )
                
                # Create wallet for admin
                db.execute_query(
                    "INSERT INTO wallets (UserID, Balance) VALUES (%s, %s)",
                    (user_id, 0.00)
                )
                
                print("Default admin user created:")
                print("Email: admin@smartloan.com")
                print("Password: admin123")
    except Exception as e:
        print(f"Error creating admin: {e}")

# Initialize default admin
create_default_admin()

def generate_loan_agreement(loan_id):
    try:
        loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
        if not loan:
            return None
            
        user = db.fetch_one("SELECT * FROM users WHERE UserID = %s", (loan['UserID'],))
        
        os.makedirs('static/agreements', exist_ok=True)
        
        filename = f"loan_agreement_{loan_id}.pdf"
        filepath = os.path.join('static', 'agreements', filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("LOAN AGREEMENT", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        emi_amount = loan['EMIAmount'] if loan['EMIAmount'] else 0
        loan_data = [
            ['Loan Agreement No:', f'LA{loan_id:06d}'],
            ['Date:', loan['AppliedDate'].strftime('%d-%m-%Y') if loan['AppliedDate'] else 'N/A'],
            ['Borrower Name:', user['Name']],
            ['Loan Amount:', f'₹{float(loan["Amount"]):,.2f}'],
            ['Interest Rate:', f'{float(loan["InterestRate"])}% per annum'],
            ['Loan Tenure:', f'{loan["Duration"]} months'],
            ['EMI Amount:', f'₹{float(emi_amount):,.2f}'],
            ['Purpose:', loan['Purpose'] or 'Not specified'],
            ['Total Repayable:', f'₹{float(emi_amount) * loan["Duration"]:,.2f}']
        ]
        
        loan_table = Table(loan_data, colWidths=[2*inch, 4*inch])
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(loan_table)
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("Terms and Conditions:", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        terms = [
            "1. The Borrower agrees to repay the loan in equated monthly installments (EMIs).",
            "2. Late payments will attract a penalty of 2% per month on the overdue amount.",
            "3. The loan can be pre-closed after 6 months with applicable charges.",
            "4. The Lender reserves the right to take legal action in case of default.",
            "5. All disputes are subject to the jurisdiction of local courts."
        ]
        
        for term in terms:
            story.append(Paragraph(term, styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
        
        story.append(Spacer(1, 0.5*inch))
        signature_data = [
            ['For Borrower:', 'For Lender:'],
            ['', ''],
            ['Signature: _________________', 'Signature: _________________'],
            ['Name: ' + user['Name'], 'Name: Loan Management System'],
            ['Date: _________________', 'Date: _________________']
        ]
        
        signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(signature_table)
        
        doc.build(story)
        
        # Update loan with agreement PDF
        db.execute_query(
            "UPDATE loans SET AgreementPDF = %s WHERE LoanID = %s",
            (filename, loan_id)
        )
        
        return filepath
        
    except Exception as e:
        print(f"Error generating agreement: {e}")
        return None

def disburse_to_wallet(loan):
    wallet = db.fetch_one("SELECT * FROM wallets WHERE UserID = %s", (loan['UserID'],))
    if not wallet:
        return False
    
    # Update wallet balance
    db.execute_query(
        "UPDATE wallets SET Balance = Balance + %s WHERE WalletID = %s",
        (loan['Amount'], wallet['WalletID'])
    )
    
    # Record transaction
    db.execute_query(
        "INSERT INTO transactions (WalletID, Amount, Type, Description, LoanID) VALUES (%s, %s, %s, %s, %s)",
        (wallet['WalletID'], loan['Amount'], 'credit', f'Loan Disbursement - {loan["LoanType"]} Loan #{loan["LoanID"]}', loan['LoanID'])
    )
    
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register_choice.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('user_type') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    # Get user loans
    loans = LoanServices.get_user_loans(session['user_id'])
    wallet = WalletServices.get_wallet_balance(session['user_id'])
    
    # Get user transactions - FIXED
    transactions = WalletServices.get_user_transactions(session['user_id'])
    
    # Calculate financial health
    borrower = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (session['user_id'],))
    health_score = 650
    factors = {}
    
    if borrower:
        base_score = borrower['CreditScore']
        if borrower['Income'] > 500000:
            base_score += 20
            factors['income'] = 'Good'
        elif borrower['Income'] > 100000:
            base_score += 10
            factors['income'] = 'Average'
        else:
            factors['income'] = 'Below Average'
        
        if borrower['EmploymentStatus'] == 'Employed':
            base_score += 30
            factors['employment'] = 'Stable'
        elif borrower['EmploymentStatus'] == 'Self-employed':
            base_score += 15
            factors['employment'] = 'Moderate'
        else:
            factors['employment'] = 'Unstable'
        
        health_score = min(max(base_score, 300), 850)
    
    # Get upcoming repayments
    upcoming_repayments = []
    active_loans = [loan for loan in loans if loan['Status'] == 'active']
    
    for loan in active_loans:
        repayments = db.fetch_all(
            "SELECT * FROM repayments WHERE LoanID = %s AND Status = 'pending' ORDER BY DueDate LIMIT 5",
            (loan['LoanID'],)
        )
        upcoming_repayments.extend(repayments)
    
    return render_template('dashboard.html', 
                         loans=loans, 
                         wallet=wallet,
                         transactions=transactions,  # ADD THIS LINE
                         health_score=health_score,
                         upcoming_repayments=upcoming_repayments,
                         factors=factors,
                         total_overdue_amount=0)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form.get('user_type', 'borrower')
        
        user = Auth.login_user(email, password, user_type)
        if user:
            session['user_id'] = user['UserID']
            session['user_name'] = user['Name']
            session['user_type'] = user['UserType']
            session['user_email'] = user['Email']
            flash(f'Welcome back, {user["Name"]}!', 'success')
            
            if user['UserType'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email, password, or user type', 'error')
    
    return render_template('login.html')

@app.route('/register/borrower', methods=['GET', 'POST'])
def register_borrower():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        income = float(request.form.get('income', 0))
        employment_status = request.form.get('employment_status', '')
        employment_type = request.form.get('employment_type', '')
        date_of_birth = request.form.get('date_of_birth')
        pan_number = request.form.get('pan_number', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        print(f"DEBUG: Registering borrower - {name}, {email}")
        
        user_id, message = Auth.register_user(name, email, password, 'borrower', phone, address)
        
        if user_id:
            print(f"DEBUG: User created with ID: {user_id}")
            # Create borrower profile
            success = Auth.register_borrower(user_id, income, employment_status, employment_type, date_of_birth, pan_number)
            print(f"DEBUG: Borrower profile creation result: {success}")
            
            if success:
                # Verify borrower was actually created
                borrower_check = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (user_id,))
                print(f"DEBUG: Borrower verification: {borrower_check}")
                
                flash('Borrower registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('User created but borrower profile failed! Please contact support.', 'error')
        else:
            flash(message, 'error')
    
    return render_template('register_borrower.html')

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/register/admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        department = request.form.get('department', '')
        permission_level = request.form.get('permission_level', 'approver')
        employee_id = request.form.get('employee_id', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        user_id, message = Auth.register_user(name, email, password, 'admin', phone, address)
        
        if user_id:
            # Create admin profile
            Auth.register_admin(user_id, department, permission_level, employee_id)
            flash('Admin registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
            return redirect(url_for('register_admin'))
    
    return render_template('register_admin.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/apply-loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if session.get('user_type') == 'admin':
        flash('Admins cannot apply for loans', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        purpose = request.form['purpose']
        duration = int(request.form['duration'])
        loan_type = request.form.get('loan_type', 'personal')
        
        # Use LoanServices to apply for loan
        loan_id, message = LoanServices.apply_loan(session['user_id'], amount, purpose, duration, loan_type)
        if loan_id:
            flash('Loan application submitted successfully!', 'success')
        else:
            flash(f'Loan application failed: {message}', 'error')
        
        return redirect(url_for('dashboard'))
    
    # DEBUG: Check borrower profile
    borrower = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (session['user_id'],))
    print(f"DEBUG: Borrower data for user {session['user_id']}: {borrower}")
    
    if not borrower:
        flash('Please complete your borrower profile first', 'error')
        return redirect(url_for('dashboard'))
    
    borrower_income = float(borrower['Income']) if borrower and borrower['Income'] else 0.0
    monthly_income = borrower_income / 12
    
    print(f"DEBUG: Borrower income: {borrower_income}, Monthly income: {monthly_income}")
    
    category_limits = {
        'DEBT_CONSOLIDATION': {
            'max_amount': monthly_income * 6,
            'description': 'Combine multiple debts into one convenient loan',
            'multiplier': 6
        },
        'HOME_IMPROVEMENT': {
            'max_amount': monthly_income * 8,
            'description': 'Renovate or improve your home with special rates', 
            'multiplier': 8
        },
        'EDUCATION': {
            'max_amount': monthly_income * 5,
            'description': 'Fund your educational expenses with lowest interest rates',
            'multiplier': 5
        },
        'BUSINESS': {
            'max_amount': monthly_income * 12,
            'description': 'Business expansion or startup capital',
            'multiplier': 12
        },
        'MEDICAL': {
            'max_amount': monthly_income * 3,
            'description': 'Medical treatment and healthcare expenses',
            'multiplier': 3
        },
        'VEHICLE_PURCHASE': {
            'max_amount': monthly_income * 4,
            'description': 'Purchase of personal or commercial vehicles',
            'multiplier': 4
        }
    }
    
    print(f"DEBUG: Category limits: {category_limits}")
    
    return render_template('apply_loan.html', category_limits=category_limits)


@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_loans = LoanServices.get_pending_loans()
    users = db.fetch_all("SELECT * FROM users")
    all_loans = db.fetch_all("SELECT * FROM loans ORDER BY AppliedDate DESC LIMIT 10")
    
    # Get admin profile for the current user
    admin_profile = db.fetch_one("""
        SELECT * FROM admins WHERE UserID = %s
    """, (session['user_id'],))
    
    print(f"🔍 ADMIN PROFILE: {admin_profile}")  # Debug line
    
    return render_template('admin_dashboard.html', 
                         pending_loans=pending_loans,
                         users=users,
                         all_loans=all_loans,
                         admin_profile=admin_profile)  # Add this line

@app.route('/api/approve-loan/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def approve_loan(loan_id):
    if LoanServices.approve_loan(loan_id):
        agreement_result = generate_loan_agreement(loan_id)
        return jsonify({
            'success': True,
            'message': 'Loan approved successfully! Agreement generated.',
            'agreement_generated': agreement_result is not None
        })
    else:
        return jsonify({'success': False, 'error': 'Loan approval failed'}), 500

@app.route('/api/reject-loan/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def reject_loan(loan_id):
    if LoanServices.reject_loan(loan_id):
        return jsonify({'success': True, 'message': 'Loan rejected successfully'})
    else:
        return jsonify({'success': False, 'error': 'Loan rejection failed'}), 500

@app.route('/admin/disburse-loans')
@login_required
@admin_required
def disburse_loans():
    approved_loans = db.fetch_all("""
        SELECT l.*, u.Name, u.Email 
        FROM loans l 
        JOIN users u ON l.UserID = u.UserID 
        WHERE l.Status = 'approved' AND l.DisbursementStatus = 'pending'
    """)
    
    return render_template('disburse_loans.html', approved_loans=approved_loans)

@app.route('/api/disburse-loan/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def disburse_loan(loan_id):
    loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
    if not loan:
        return jsonify({'error': 'Loan not found'}), 404
    
    if loan['Status'] != 'approved':
        return jsonify({'error': 'Loan must be approved before disbursement'}), 400
    
    if not loan['AgreementSigned']:
        return jsonify({'error': 'Borrower must sign the agreement before disbursement'}), 400
    
    if loan['DisbursementStatus'] == 'processed':
        return jsonify({'error': 'Loan already disbursed'}), 400
    
    data = request.get_json()
    disbursement_method = data.get('method', 'wallet')
    
    try:
        if disbursement_method == 'wallet':
            success = disburse_to_wallet(loan)
        else:
            return jsonify({'error': 'Invalid disbursement method'}), 400
        
        if success:
            db.execute_query(
                "UPDATE loans SET DisbursementStatus = 'processed', DisbursedDate = %s, DisbursementMethod = %s, Status = 'active' WHERE LoanID = %s",
                (datetime.now(), disbursement_method, loan_id)
            )
            return jsonify({'success': True, 'message': 'Loan disbursed successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Disbursement failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/agreement/<int:loan_id>')
@login_required
def view_agreement(loan_id):
    loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
    
    if not loan:
        flash('Loan not found', 'error')
        return redirect(url_for('dashboard'))
    
    if session.get('user_type') != 'admin' and loan['UserID'] != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if not loan['AgreementPDF']:
        flash('Agreement not generated yet', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('view_agreement.html', loan=loan)

@app.route('/download-agreement/<int:loan_id>')
@login_required
def download_agreement(loan_id):
    loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
    
    if not loan:
        flash('Loan not found', 'error')
        return redirect(url_for('dashboard'))
    
    if session.get('user_type') != 'admin' and loan['UserID'] != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if loan['AgreementPDF'] and os.path.exists(os.path.join('static/agreements', loan['AgreementPDF'])):
        return send_from_directory('static/agreements', loan['AgreementPDF'], as_attachment=True)
    else:
        flash('Agreement not found', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/sign-agreement/<int:loan_id>', methods=['POST'])
@login_required
def sign_agreement(loan_id):
    if session.get('user_type') == 'admin':
        return jsonify({'error': 'Only borrowers can sign agreements'}), 403
    
    loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
    if not loan:
        return jsonify({'error': 'Loan not found'}), 404
    
    if loan['UserID'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.execute_query(
        "UPDATE loans SET AgreementSigned = 1, SignedDate = %s WHERE LoanID = %s",  # 1 instead of TRUE
        (datetime.now(), loan_id)
    )
    
    return jsonify({'success': True, 'message': 'Agreement signed successfully'})

@app.route('/api/repay-emi/<int:repayment_id>', methods=['POST'])
@login_required
def repay_emi(repayment_id):
    if session.get('user_type') == 'admin':
        return jsonify({'error': 'Admins cannot make payments'}), 403
    
    success, message = WalletServices.repay_emi(repayment_id, session['user_id'])
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/add-wallet-funds', methods=['POST'])
@login_required
def add_wallet_funds():
    if session.get('user_type') == 'admin':
        return jsonify({'success': False, 'error': 'Admins cannot add funds to wallet'}), 403
    
    data = request.get_json()
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400
    
    # Get user's wallet
    wallet = db.fetch_one("SELECT * FROM wallets WHERE UserID = %s", (session['user_id'],))
    if not wallet:
        return jsonify({'success': False, 'error': 'Wallet not found'}), 404
    
    try:
        # Update wallet balance
        db.execute_query(
            "UPDATE wallets SET Balance = Balance + %s WHERE WalletID = %s",
            (amount, wallet['WalletID'])
        )
        
        # Record transaction - MAKE SURE THIS IS WORKING
        transaction_id = db.execute_query(
            "INSERT INTO transactions (WalletID, Amount, Type, Description, Status) VALUES (%s, %s, %s, %s, %s)",
            (wallet['WalletID'], amount, 'credit', 'Wallet top-up', 'completed')
        )
        
        if transaction_id:
            # Get updated wallet balance
            updated_wallet = db.fetch_one("SELECT * FROM wallets WHERE WalletID = %s", (wallet['WalletID'],))
            return jsonify({
                'success': True, 
                'message': f'₹{amount:.2f} added to wallet successfully',
                'new_balance': float(updated_wallet['Balance'])
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to record transaction'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/make-admin/<int:user_id>')
@login_required
@admin_required
def make_admin(user_id):
    # Check if current user is super admin
    current_admin = db.fetch_one("SELECT * FROM admins WHERE UserID = %s", (session['user_id'],))
    if not current_admin or current_admin['PermissionLevel'] != 'super_admin':
        flash('Access denied - Super Admin privileges required', 'error')
        return redirect(url_for('dashboard'))
    
    user = db.fetch_one("SELECT * FROM users WHERE UserID = %s", (user_id,))
    if user and user['UserType'] == 'borrower':
        # Update user type
        db.execute_query("UPDATE users SET UserType = 'admin' WHERE UserID = %s", (user_id,))
        
        # Create admin profile
        db.execute_query(
            "INSERT INTO admins (UserID, Department, PermissionLevel, EmployeeID) VALUES (%s, %s, %s, %s)",
            (user_id, 'General', 'viewer', f'EMP{user_id:03d}')
        )
        
        flash(f'{user["Name"]} is now an admin', 'success')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
