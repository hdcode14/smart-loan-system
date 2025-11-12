
from datetime import datetime, date, timedelta
from database import db
import math

class UserModel:
    @staticmethod
    def create_user(name, email, password, user_type, phone=None, address=None):
        query = """
        INSERT INTO users (Name, Email, PasswordHash, UserType, Phone, Address) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        from auth import Auth  # Assuming you have Auth class for password hashing
        password_hash = Auth.hash_password(password)
        return db.execute_query(query, (name, email, password_hash, user_type, phone, address))
    
    @staticmethod
    def get_user_by_email(email):
        return db.fetch_one("SELECT * FROM users WHERE Email = %s", (email,))
    
    @staticmethod
    def get_user_by_id(user_id):
        return db.fetch_one("SELECT * FROM users WHERE UserID = %s", (user_id,))
    
    @staticmethod
    def is_borrower(user):
        return user and user['UserType'] == 'borrower'
    
    @staticmethod
    def is_admin(user):
        return user and user['UserType'] == 'admin'

class BorrowerModel:
    @staticmethod
    def create_borrower(user_id, income, employment_status, employment_type, date_of_birth, pan_number):
        query = """
        INSERT INTO borrowers (UserID, Income, EmploymentStatus, EmploymentType, DateOfBirth, PANNumber) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return db.execute_query(query, (user_id, income, employment_status, employment_type, date_of_birth, pan_number))
    
    @staticmethod
    def get_borrower_by_user_id(user_id):
        return db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (user_id,))
    
    @staticmethod
    def calculate_financial_health(borrower):
        if not borrower:
            return 650, {}
        
        base_score = borrower['CreditScore']
        factors = {}
        
        # Income factor
        income = float(borrower['Income'])
        if income > 500000:
            base_score += 20
            factors['income'] = 'Good'
        elif income > 100000:
            base_score += 10
            factors['income'] = 'Average'
        else:
            factors['income'] = 'Below Average'
        
        # Employment factor
        if borrower['EmploymentStatus'] == 'Employed':
            base_score += 30
            factors['employment'] = 'Stable'
        elif borrower['EmploymentStatus'] == 'Self-employed':
            base_score += 15
            factors['employment'] = 'Moderate'
        else:
            factors['employment'] = 'Unstable'
        
        # Loan history factor
        loans_count = LoanModel.get_user_loans_count(borrower['UserID'])
        if loans_count == 0:
            base_score += 10
            factors['loan_history'] = 'No previous loans'
        else:
            paid_loans = LoanModel.get_completed_loans_count(borrower['UserID'])
            if paid_loans == loans_count:
                base_score += 25
                factors['loan_history'] = 'Excellent repayment'
            else:
                base_score -= 10
                factors['loan_history'] = 'Poor repayment history'
        
        score = min(max(base_score, 300), 850)
        return score, factors

class LoanModel:
    @staticmethod
    def apply_loan(user_id, amount, purpose, duration, loan_type='personal'):
        # Calculate interest rate based on category and credit score
        borrower = BorrowerModel.get_borrower_by_user_id(user_id)
        if not borrower:
            return None
        
        credit_score = borrower['CreditScore']
        interest_rate = LoanModel.calculate_category_interest_rate(purpose, credit_score)
        
        query = """
        INSERT INTO loans (UserID, Amount, InterestRate, Duration, LoanType, Purpose, Status) 
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """
        loan_id = db.execute_query(query, (user_id, amount, interest_rate, duration, loan_type, purpose))
        
        if loan_id:
            # Generate repayment schedule
            LoanModel.generate_repayment_schedule(loan_id, amount, interest_rate, duration)
        
        return loan_id
    
    @staticmethod
    def calculate_category_interest_rate(purpose, credit_score):
        base_rates = {
            'DEBT_CONSOLIDATION': 7.0,
            'HOME_IMPROVEMENT': 6.0,
            'EDUCATION': 5.5,
            'BUSINESS': 8.0,
            'MEDICAL': 6.5,
            'VEHICLE_PURCHASE': 7.5
        }
        
        base_rate = base_rates.get(purpose, 7.0)
        
        # Adjust based on credit score
        if credit_score >= 750:
            return base_rate - 1.0
        elif credit_score >= 650:
            return base_rate - 0.5
        elif credit_score < 600:
            return base_rate + 1.5
        else:
            return base_rate
    
    @staticmethod
    def generate_repayment_schedule(loan_id, amount, interest_rate, duration):
        try:
            # Calculate EMI
            monthly_rate = interest_rate / 100 / 12
            emi = amount * monthly_rate * (1 + monthly_rate) ** duration / ((1 + monthly_rate) ** duration - 1)
            emi = round(emi, 2)
            
            # Update loan with EMI amount
            db.execute_query(
                "UPDATE loans SET EMIAmount = %s, OutstandingBalance = %s WHERE LoanID = %s",
                (emi, amount, loan_id)
            )
            
            balance = float(amount)
            
            # Generate repayment schedule
            for i in range(duration):
                interest = balance * monthly_rate
                principal = emi - interest
                balance -= principal
                
                due_date = datetime.now() + timedelta(days=30*(i+1))
                
                db.execute_query("""
                    INSERT INTO repayments (LoanID, DueDate, Amount, PrincipalAmount, InterestAmount, Status, TotalAmountDue)
                    VALUES (%s, %s, %s, %s, %s, 'pending', %s)
                """, (loan_id, due_date.date(), emi, round(principal, 2), round(interest, 2), emi))
            
            return True
        except Exception as e:
            print(f"Error generating repayment schedule: {e}")
            return False
    
    @staticmethod
    def get_user_loans(user_id):
        return db.fetch_all("SELECT * FROM loans WHERE UserID = %s ORDER BY AppliedDate DESC", (user_id,))
    
    @staticmethod
    def get_user_loans_count(user_id):
        result = db.fetch_one("SELECT COUNT(*) as count FROM loans WHERE UserID = %s", (user_id,))
        return result['count'] if result else 0
    
    @staticmethod
    def get_completed_loans_count(user_id):
        result = db.fetch_one("SELECT COUNT(*) as count FROM loans WHERE UserID = %s AND Status = 'completed'", (user_id,))
        return result['count'] if result else 0
    
    @staticmethod
    def approve_loan(loan_id):
        return db.execute_query(
            "UPDATE loans SET Status = 'approved', ApprovedDate = %s WHERE LoanID = %s",
            (datetime.now(), loan_id)
        )
    
    @staticmethod
    def reject_loan(loan_id):
        return db.execute_query(
            "UPDATE loans SET Status = 'rejected' WHERE LoanID = %s",
            (loan_id,)
        )
    
    @staticmethod
    def get_pending_loans():
        return db.fetch_all("""
            SELECT l.*, u.Name, u.Email 
            FROM loans l 
            JOIN users u ON l.UserID = u.UserID 
            WHERE l.Status = 'pending'
        """)
    
    @staticmethod
    def can_disburse(loan_id):
        loan = db.fetch_one("""
            SELECT Status, AgreementSigned, DisbursementStatus 
            FROM loans WHERE LoanID = %s
        """, (loan_id,))
        
        return (loan and 
                loan['Status'] == 'approved' and 
                loan['AgreementSigned'] and 
                loan['DisbursementStatus'] in ['pending', 'signed'])

class WalletModel:
    @staticmethod
    def create_wallet(user_id):
        return db.execute_query("INSERT INTO wallets (UserID) VALUES (%s)", (user_id,))
    
    @staticmethod
    def get_wallet_balance(user_id):
        return db.fetch_one("SELECT * FROM wallets WHERE UserID = %s", (user_id,))
    
    @staticmethod
    def add_funds(wallet_id, amount):
        return db.execute_query(
            "UPDATE wallets SET Balance = Balance + %s, LastUpdated = %s WHERE WalletID = %s",
            (amount, datetime.now(), wallet_id)
        )
    
    @staticmethod
    def repay_emi(repayment_id, user_id):
        # Get repayment details
        repayment = db.fetch_one("""
            SELECT r.*, l.UserID, l.LoanID 
            FROM repayments r 
            JOIN loans l ON r.LoanID = l.LoanID 
            WHERE r.RepaymentID = %s
        """, (repayment_id,))
        
        if not repayment or repayment['UserID'] != user_id:
            return False, "Unauthorized or repayment not found"
        
        # Check if already paid
        if repayment['Status'] == 'paid':
            return False, "EMI already paid"
        
        # Calculate late penalty if overdue
        total_amount_due = WalletModel.calculate_late_penalty(repayment_id)
        
        # Get wallet balance
        wallet = WalletModel.get_wallet_balance(user_id)
        if not wallet or float(wallet['Balance']) < total_amount_due:
            return False, f"Insufficient balance. Required: ₹{total_amount_due:.2f}"
        
        # Process payment
        try:
            # Deduct from wallet
            db.execute_query(
                "UPDATE wallets SET Balance = Balance - %s WHERE WalletID = %s",
                (total_amount_due, wallet['WalletID'])
            )
            
            # Update repayment status
            db.execute_query(
                "UPDATE repayments SET Status = 'paid', PaidDate = %s, TotalAmountDue = %s WHERE RepaymentID = %s",
                (datetime.now(), total_amount_due, repayment_id)
            )
            
            # Record transaction
            description = f'EMI Payment for Loan #{repayment["LoanID"]}'
            if total_amount_due > float(repayment['Amount']):
                penalty = total_amount_due - float(repayment['Amount'])
                description += f' (Includes ₹{penalty:.2f} late penalty)'
            
            db.execute_query("""
                INSERT INTO transactions (WalletID, Amount, Type, Description, LoanID)
                VALUES (%s, %s, 'debit', %s, %s)
            """, (wallet['WalletID'], total_amount_due, description, repayment['LoanID']))
            
            # Check if loan is fully paid
            remaining = db.fetch_one("""
                SELECT COUNT(*) as count FROM repayments 
                WHERE LoanID = %s AND Status = 'pending'
            """, (repayment['LoanID'],))
            
            if remaining and remaining['count'] == 0:
                db.execute_query(
                    "UPDATE loans SET Status = 'completed', OutstandingBalance = 0 WHERE LoanID = %s",
                    (repayment['LoanID'],)
                )
            
            return True, "EMI paid successfully"
            
        except Exception as e:
            return False, f"Payment failed: {str(e)}"
    
    @staticmethod
    def calculate_late_penalty(repayment_id):
        repayment = db.fetch_one("SELECT * FROM repayments WHERE RepaymentID = %s", (repayment_id,))
        if not repayment:
            return 0
        
        due_date = repayment['DueDate']
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        
        if repayment['Status'] == 'pending' and due_date < datetime.now().date():
            days_overdue = (datetime.now().date() - due_date).days
            
            # 2% penalty per month on overdue amount
            penalty_rate = 0.02
            monthly_penalty = float(repayment['Amount']) * penalty_rate
            daily_penalty = monthly_penalty / 30
            penalty = daily_penalty * days_overdue
            
            # Update repayment with penalty
            db.execute_query(
                "UPDATE repayments SET LatePenalty = %s, DaysOverdue = %s, TotalAmountDue = %s WHERE RepaymentID = %s",
                (penalty, days_overdue, float(repayment['Amount']) + penalty, repayment_id)
            )
            
            return float(repayment['Amount']) + penalty
        else:
            return float(repayment['Amount'])