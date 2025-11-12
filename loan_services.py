from datetime import datetime, timedelta
import math
from database import db

class LoanServices:
    
    @staticmethod
    def apply_loan(user_id, amount, purpose, duration, loan_type='personal'):
        """
        Apply for a new loan with validation and automatic interest rate calculation
        """
        try:
            # Get borrower profile to check eligibility
            borrower = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (user_id,))
            if not borrower:
                return None, "Borrower profile not found"
            
            credit_score = borrower['CreditScore']
            
            # Check credit score eligibility
            if credit_score < 600:
                return None, "Credit score too low for loan application"
            
            # Calculate interest rate based on purpose and credit score
            interest_rate = LoanServices.calculate_interest_rate(purpose, credit_score)
            
            # Validate loan amount against category limits
            is_valid, message = LoanServices.validate_loan_amount(user_id, amount, purpose)
            if not is_valid:
                return None, message
            
            # Insert loan application
            query = """
            INSERT INTO loans (UserID, Amount, InterestRate, Duration, LoanType, Purpose, Status) 
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """
            loan_id = db.execute_query(query, (user_id, amount, interest_rate, duration, loan_type, purpose))
            
            if loan_id:
                # Generate repayment schedule
                success = LoanServices.generate_repayment_schedule(loan_id, amount, interest_rate, duration)
                if not success:
                    return None, "Loan application submitted but failed to generate repayment schedule"
                
                return loan_id, "Loan application submitted successfully"
            else:
                return None, "Failed to submit loan application"
                
        except Exception as e:
            return None, f"Error applying for loan: {str(e)}"
    
    @staticmethod
    def calculate_interest_rate(purpose, credit_score):
        """
        Calculate interest rate based on loan purpose and credit score
        """
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
    def validate_loan_amount(user_id, amount, purpose):
        """
        Validate loan amount against category limits and borrower income
        """
        try:
            borrower = db.fetch_one("SELECT Income FROM borrowers WHERE UserID = %s", (user_id,))
            if not borrower:
                return False, "Borrower profile not found"
            
            borrower_income = float(borrower['Income']) if borrower['Income'] else 0.0
            monthly_income = borrower_income / 12
            
            # Category-based limits (conservative multipliers)
            category_limits = {
                'DEBT_CONSOLIDATION': monthly_income * 6,
                'HOME_IMPROVEMENT': monthly_income * 8,
                'EDUCATION': monthly_income * 5,
                'BUSINESS': monthly_income * 12,
                'MEDICAL': monthly_income * 3,
                'VEHICLE_PURCHASE': monthly_income * 4
            }
            
            max_amount = category_limits.get(purpose, monthly_income * 6)
            
            if amount > max_amount:
                return False, f"Maximum amount for {purpose.replace('_', ' ').title()} is ₹{max_amount:,.2f} based on your income"
            
            return True, "Valid amount"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def generate_repayment_schedule(loan_id, amount, interest_rate, duration):
        """
        Generate EMI repayment schedule for the loan
        """
        try:
            # Calculate EMI using standard formula
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
        """
        Get all loans for a user
        """
        return db.fetch_all("SELECT * FROM loans WHERE UserID = %s ORDER BY AppliedDate DESC", (user_id,))
    
    @staticmethod
    def get_pending_loans():
        """
        Get all pending loans for admin approval
        """
        return db.fetch_all("""
            SELECT l.*, u.Name, u.Email 
            FROM loans l 
            JOIN users u ON l.UserID = u.UserID 
            WHERE l.Status = 'pending'
        """)
    
    @staticmethod
    def approve_loan(loan_id):
        """
        Approve a loan application
        """
        try:
            success = db.execute_query(
                "UPDATE loans SET Status = 'approved', ApprovedDate = %s WHERE LoanID = %s",
                (datetime.now(), loan_id)
            )
            return success is not None
        except Exception as e:
            print(f"Error approving loan: {e}")
            return False
    
    @staticmethod
    def reject_loan(loan_id):
        """
        Reject a loan application
        """
        try:
            success = db.execute_query(
                "UPDATE loans SET Status = 'rejected' WHERE LoanID = %s",
                (loan_id,)
            )
            return success is not None
        except Exception as e:
            print(f"Error rejecting loan: {e}")
            return False
    
    @staticmethod
    def can_disburse_loan(loan_id):
        """
        Check if loan is ready for disbursement (approved + agreement signed)
        """
        loan = db.fetch_one("""
            SELECT Status, AgreementSigned, DisbursementStatus 
            FROM loans WHERE LoanID = %s
        """, (loan_id,))
        
        # FIX: Convert MySQL 0/1 to boolean and check ENUM values
        return (loan and 
                loan['Status'] == 'approved' and 
                bool(loan['AgreementSigned']) and  # Convert 0/1 to True/False
                loan['DisbursementStatus'] in ['pending', 'signed'])
    
    @staticmethod
    def disburse_loan(loan_id, disbursement_method='wallet'):
        """
        Disburse loan amount to borrower
        """
        try:
            loan = db.fetch_one("SELECT * FROM loans WHERE LoanID = %s", (loan_id,))
            if not loan:
                return False, "Loan not found"
            
            # Check if loan can be disbursed
            if not LoanServices.can_disburse_loan(loan_id):
                return False, "Loan not ready for disbursement"
            
            # Process disbursement based on method
            if disbursement_method == 'wallet':
                success = LoanServices.disburse_to_wallet(loan)
            else:
                return False, "Invalid disbursement method"
            
            if success:
                # Update loan status
                db.execute_query(
                    "UPDATE loans SET DisbursementStatus = 'processed', DisbursedDate = %s, DisbursementMethod = %s, Status = 'active' WHERE LoanID = %s",
                    (datetime.now(), disbursement_method, loan_id)
                )
                return True, "Loan disbursed successfully"
            else:
                return False, "Disbursement failed"
                
        except Exception as e:
            return False, f"Disbursement error: {str(e)}"
    
    @staticmethod
    def disburse_to_wallet(loan):
        """
        Disburse loan amount to borrower's wallet
        """
        try:
            wallet = db.fetch_one("SELECT * FROM wallets WHERE UserID = %s", (loan['UserID'],))
            if not wallet:
                return False
            
            # Add loan amount to wallet
            db.execute_query(
                "UPDATE wallets SET Balance = Balance + %s, LastUpdated = %s WHERE WalletID = %s",
                (loan['Amount'], datetime.now(), wallet['WalletID'])
            )
            
            # Record transaction
            db.execute_query("""
                INSERT INTO transactions (WalletID, Amount, Type, Description, LoanID)
                VALUES (%s, %s, 'credit', %s, %s)
            """, (wallet['WalletID'], loan['Amount'], f'Loan Disbursement - {loan["LoanType"]} Loan #{loan["LoanID"]}', loan['LoanID']))
            
            return True
            
        except Exception as e:
            print(f"Error disbursing to wallet: {e}")
            return False
    
    @staticmethod
    def calculate_emi(principal, interest_rate, tenure_months):
        """
        Calculate EMI amount
        """
        monthly_rate = interest_rate / 100 / 12
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
        return round(emi, 2)
    
    @staticmethod
    def get_loan_summary(user_id):
        """
        Get loan summary for dashboard
        """
        loans = LoanServices.get_user_loans(user_id)
        
        summary = {
            'total_loans': len(loans),
            'active_loans': len([loan for loan in loans if loan['Status'] == 'active']),
            'pending_loans': len([loan for loan in loans if loan['Status'] == 'pending']),
            'total_borrowed': sum(float(loan['Amount']) for loan in loans if loan['Status'] in ['active', 'completed']),
            'outstanding_balance': sum(float(loan['OutstandingBalance']) for loan in loans if loan['Status'] == 'active')
        }
        
        return summary
    
    @staticmethod
    def get_upcoming_repayments(user_id, limit=5):
        """
        Get upcoming repayments for user
        """
        return db.fetch_all("""
            SELECT r.*, l.LoanID, l.LoanType 
            FROM repayments r 
            JOIN loans l ON r.LoanID = l.LoanID 
            WHERE l.UserID = %s AND r.Status = 'pending' 
            ORDER BY r.DueDate 
            LIMIT %s
        """, (user_id, limit))
    
    @staticmethod
    def check_overdue_repayments(loan_id):
        """
        Check and update overdue repayments with penalties
        """
        try:
            overdue_repayments = db.fetch_all("""
                SELECT * FROM repayments 
                WHERE LoanID = %s AND Status = 'pending' AND DueDate < %s
            """, (loan_id, datetime.now().date()))
            
            total_penalty = 0
            for repayment in overdue_repayments:
                penalty = LoanServices.calculate_late_penalty(repayment['RepaymentID'])
                total_penalty += penalty
            
            return total_penalty, len(overdue_repayments)
            
        except Exception as e:
            print(f"Error checking overdue repayments: {e}")
            return 0, 0
    
    @staticmethod
    def calculate_late_penalty(repayment_id):
        """
        Calculate late penalty for overdue repayment
        """
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
            
            return penalty
        else:
            return 0