from datetime import datetime
from database import db

class WalletServices:
    
    @staticmethod
    def get_wallet_balance(user_id):
        """Get wallet balance for user"""
        return db.fetch_one("SELECT * FROM wallets WHERE UserID = %s", (user_id,))
    
    @staticmethod
    def get_user_transactions(user_id, limit=10):
        """Get recent transactions for user"""
        return db.fetch_all("""
            SELECT t.*, w.UserID 
            FROM transactions t 
            JOIN wallets w ON t.WalletID = w.WalletID 
            WHERE w.UserID = %s 
            ORDER BY t.TransactionDate DESC 
            LIMIT %s
        """, (user_id, limit))
    
    @staticmethod
    def repay_emi(repayment_id, user_id):
        """Repay EMI from wallet balance"""
        try:
            # Get repayment details with loan info
            repayment = db.fetch_one("""
                SELECT r.*, l.UserID, l.LoanID, l.LoanType 
                FROM repayments r 
                JOIN loans l ON r.LoanID = l.LoanID 
                WHERE r.RepaymentID = %s
            """, (repayment_id,))
            
            if not repayment or repayment['UserID'] != user_id:
                return False, "Unauthorized or repayment not found"
            
            # Check if already paid
            if repayment['Status'] == 'paid':
                return False, "EMI already paid"
            
            # Calculate total amount due (including penalty)
            total_amount_due = WalletServices.calculate_late_penalty(repayment_id)
            
            # Get wallet balance
            wallet = WalletServices.get_wallet_balance(user_id)
            if not wallet or float(wallet['Balance']) < total_amount_due:
                penalty_msg = ""
                if total_amount_due > float(repayment['Amount']):
                    penalty = total_amount_due - float(repayment['Amount'])
                    penalty_msg = f" (includes ₹{penalty:.2f} late penalty)"
                return False, f"Insufficient balance. Required: ₹{total_amount_due:.2f}{penalty_msg}"
            
            # Process payment
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
            description = f'EMI Payment - {repayment["LoanType"]} Loan #{repayment["LoanID"]}'
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
                return True, "Congratulations! Loan fully paid!"
            else:
                return True, "EMI paid successfully!"
                
        except Exception as e:
            return False, f"Payment failed: {str(e)}"
    
    @staticmethod
    def calculate_late_penalty(repayment_id):
        """Calculate late penalty for overdue repayment"""
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