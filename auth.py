import hashlib
from database import db

class Auth:
    @staticmethod
    def hash_password(password):
        salt = "smart_loan_system_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, hashed):
        return Auth.hash_password(password) == hashed
    
    @staticmethod
    def login_user(email, password, user_type='borrower'):
        query = "SELECT * FROM users WHERE Email = %s AND UserType = %s"
        user = db.fetch_one(query, (email, user_type))
        
        if user and Auth.verify_password(password, user['PasswordHash']):
            return user
        return None
    
    @staticmethod
    def register_user(name, email, password, user_type, phone=None, address=None):
        existing = db.fetch_one("SELECT UserID FROM users WHERE Email = %s", (email,))
        if existing:
            return None, "Email already registered"
        
        query = """
        INSERT INTO users (Name, Email, PasswordHash, UserType, Phone, Address) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        user_id = db.execute_query(query, (name, email, Auth.hash_password(password), user_type, phone, address))
        
        if user_id:
            wallet_query = "INSERT INTO wallets (UserID, Balance) VALUES (%s, %s)"
            db.execute_query(wallet_query, (user_id, 0.0))
            return user_id, "Registration successful"
        return None, "Registration failed"
    
    @staticmethod
    def register_borrower(user_id, income, employment_status, employment_type, date_of_birth, pan_number):
        try:
            print(f"🚨 DEBUG BORROWER REGISTRATION:")
            print(f"📝 UserID: {user_id}")
            print(f"💰 Income: {income} (type: {type(income)})")
            print(f"💼 Employment Status: '{employment_status}'")
            print(f"🏢 Employment Type: '{employment_type}'")
            print(f"🎂 Date of Birth: '{date_of_birth}' (type: {type(date_of_birth)})")
            print(f"🆔 PAN Number: '{pan_number}'")
            
            # Check if user exists
            user_check = db.fetch_one("SELECT * FROM users WHERE UserID = %s", (user_id,))
            print(f"👤 User exists check: {user_check is not None}")
            
            query = """
            INSERT INTO borrowers (UserID, Income, EmploymentStatus, EmploymentType, DateOfBirth, PANNumber, CreditScore) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Set default credit score
            credit_score = 650
            
            print(f"🔍 Executing query: {query}")
            print(f"🔍 With params: ({user_id}, {income}, '{employment_status}', '{employment_type}', '{date_of_birth}', '{pan_number}', {credit_score})")
            
            result = db.execute_query(query, (user_id, income, employment_status, employment_type, date_of_birth, pan_number, credit_score))
            print(f"✅ Borrower insert result: {result}")
            
            if result:
                # Verify it was actually inserted
                verify = db.fetch_one("SELECT * FROM borrowers WHERE UserID = %s", (user_id,))
                print(f"🔍 Verification: {verify}")
            
            return result is not None
            
        except Exception as e:
            print(f"❌ ERROR creating borrower: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def register_admin(user_id, department, permission_level, employee_id):
        query = """
        INSERT INTO admins (UserID, Department, PermissionLevel, EmployeeID) 
        VALUES (%s, %s, %s, %s)
        """
        result = db.execute_query(query, (user_id, department, permission_level, employee_id))
        return result is not None