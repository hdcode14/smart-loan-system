import mysql.connector
from mysql.connector import Error
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database')

class Database:
    def __init__(self, config):
        self.config = config
        self.connection = None
        
    def connect(self):
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(**self.config)
                logger.info("Connected to MySQL database")
            return self.connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def execute_query(self, query, params=None):
        connection = self.connect()
        if not connection:
            return None
            
        cursor = None
        try:
            cursor = connection.cursor(buffered=True)
            cursor.execute(query, params or ())
            connection.commit()
            return cursor.lastrowid
        except Error as e:
            logger.error(f"Query error: {e}")
            connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def fetch_one(self, query, params=None):
        connection = self.connect()
        if not connection:
            return None
            
        cursor = None
        try:
            cursor = connection.cursor(buffered=True, dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchone()
            return result
        except Error as e:
            logger.error(f"Fetch one error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def fetch_all(self, query, params=None):
        connection = self.connect()
        if not connection:
            return None
            
        cursor = None
        try:
            cursor = connection.cursor(buffered=True, dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
        except Error as e:
            logger.error(f"Fetch all error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

def create_tables_if_not_exist():
    """Create all required tables if they don't exist"""
    try:
        logger.info("Checking if database tables exist...")
        
        # Check if users table exists
        result = db.fetch_one("SHOW TABLES LIKE 'users'")
        if result:
            logger.info("✅ Database tables already exist")
            return True
        
        logger.info("Creating database tables...")
        
        # Create users table
        db.execute_query('''
            CREATE TABLE users (
                UserID INT AUTO_INCREMENT PRIMARY KEY,
                Name VARCHAR(100) NOT NULL,
                Email VARCHAR(120) UNIQUE NOT NULL,
                PasswordHash VARCHAR(200) NOT NULL,
                UserType ENUM('borrower', 'admin') NOT NULL,
                Phone VARCHAR(15),
                Address VARCHAR(200),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (Email),
                INDEX idx_user_type (UserType)
            )
        ''')
        
        # Create borrowers table
        db.execute_query('''
            CREATE TABLE borrowers (
                UserID INT PRIMARY KEY,
                Income DECIMAL(15,2) DEFAULT 0.00,
                CreditScore INT DEFAULT 650,
                EmploymentStatus VARCHAR(50),
                EmploymentType VARCHAR(20),
                DateOfBirth DATE,
                PANNumber VARCHAR(10),
                FOREIGN KEY (UserID) REFERENCES users(UserID) ON DELETE CASCADE,
                INDEX idx_credit_score (CreditScore)
            )
        ''')
        
        # Create admins table
        db.execute_query('''
            CREATE TABLE admins (
                UserID INT PRIMARY KEY,
                Department VARCHAR(50),
                PermissionLevel ENUM('viewer', 'approver', 'super_admin') DEFAULT 'approver',
                EmployeeID VARCHAR(50),
                FOREIGN KEY (UserID) REFERENCES users(UserID) ON DELETE CASCADE
            )
        ''')
        
        # Create loans table
        db.execute_query('''
            CREATE TABLE loans (
                LoanID INT AUTO_INCREMENT PRIMARY KEY,
                UserID INT NOT NULL,
                Amount DECIMAL(15,2) NOT NULL,
                InterestRate DECIMAL(5,2) NOT NULL,
                Duration INT NOT NULL,
                Status ENUM('pending', 'approved', 'rejected', 'active', 'completed') DEFAULT 'pending',
                LoanType ENUM('personal', 'business', 'education', 'home') DEFAULT 'personal',
                Purpose VARCHAR(100),
                AppliedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ApprovedDate TIMESTAMP NULL,
                DisbursedDate TIMESTAMP NULL,
                EMIAmount DECIMAL(15,2),
                OutstandingBalance DECIMAL(15,2) DEFAULT 0.00,
                DisbursementStatus ENUM('pending', 'signed', 'processed') DEFAULT 'pending',
                DisbursementMethod VARCHAR(20),
                AgreementPDF VARCHAR(200),
                AgreementSigned TINYINT(1) DEFAULT 0,
                SignedDate TIMESTAMP NULL,
                CompletionDate TIMESTAMP NULL,
                CompletionMessage VARCHAR(500),
                FOREIGN KEY (UserID) REFERENCES users(UserID) ON DELETE CASCADE,
                INDEX idx_loan_status (Status),
                INDEX idx_user_loans (UserID)
            )
        ''')
        
        # Create repayments table
        db.execute_query('''
            CREATE TABLE repayments (
                RepaymentID INT AUTO_INCREMENT PRIMARY KEY,
                LoanID INT NOT NULL,
                DueDate DATE NOT NULL,
                Amount DECIMAL(15,2) NOT NULL,
                PrincipalAmount DECIMAL(15,2),
                InterestAmount DECIMAL(15,2),
                Status ENUM('pending', 'paid', 'overdue') DEFAULT 'pending',
                PaidDate TIMESTAMP NULL,
                LatePenalty DECIMAL(15,2) DEFAULT 0.00,
                DaysOverdue INT DEFAULT 0,
                TotalAmountDue DECIMAL(15,2),
                FOREIGN KEY (LoanID) REFERENCES loans(LoanID) ON DELETE CASCADE,
                INDEX idx_repayment_due (DueDate),
                INDEX idx_repayment_status (Status)
            )
        ''')
        
        # Create wallets table
        db.execute_query('''
            CREATE TABLE wallets (
                WalletID INT AUTO_INCREMENT PRIMARY KEY,
                UserID INT NOT NULL UNIQUE,
                Balance DECIMAL(15,2) DEFAULT 0.00,
                SavingsBalance DECIMAL(15,2) DEFAULT 0.00,
                LastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (UserID) REFERENCES users(UserID) ON DELETE CASCADE,
                INDEX idx_user_wallet (UserID)
            )
        ''')
        
        # Create transactions table
        db.execute_query('''
            CREATE TABLE transactions (
                TransactionID INT AUTO_INCREMENT PRIMARY KEY,
                WalletID INT NOT NULL,
                Amount DECIMAL(15,2) NOT NULL,
                Type ENUM('credit', 'debit'),
                Description VARCHAR(200),
                TransactionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                LoanID INT,
                Status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
                FOREIGN KEY (WalletID) REFERENCES wallets(WalletID) ON DELETE CASCADE,
                FOREIGN KEY (LoanID) REFERENCES loans(LoanID) ON DELETE SET NULL,
                INDEX idx_transaction_date (TransactionDate)
            )
        ''')
        
        # Create default admin user
        db.execute_query('''
            INSERT INTO users (Name, Email, PasswordHash, UserType, Phone, Address) 
            VALUES ('System Administrator', 'admin@smartloan.com', 'b2b4d1bb3ab6484d3af6154ae1b9026548af1d1a5e1631c14d1e7316ba002ac6', 'admin', '+1-555-0001', '123 Admin Street, City, State')
        ''')
        
        # Get the last inserted admin user ID
        result = db.fetch_one('SELECT LAST_INSERT_ID() as id')
        admin_id = result['id'] if result else 1
        
        db.execute_query('''
            INSERT INTO admins (UserID, Department, PermissionLevel, EmployeeID) 
            VALUES (%s, 'Administration', 'super_admin', 'ADM001')
        ''', (admin_id,))
        
        db.execute_query('''
            INSERT INTO wallets (UserID, Balance) 
            VALUES (%s, 0.00)
        ''', (admin_id,))
        
        logger.info("✅ All database tables created successfully!")
        logger.info("✅ Default admin user created: admin@smartloan.com / admin123")
        return True
        
    except Exception as e:
        logger.error(f"❌ Table creation error: {e}")
        return False

# Database configuration - USING RAILWAY ENVIRONMENT VARIABLES
db_config = {
    'host': os.getenv('MYSQLHOST', 'localhost'),
    'port': int(os.getenv('MYSQLPORT', 3306)),
    'user': os.getenv('MYSQLUSER', 'root'),
    'password': os.getenv('MYSQLPASSWORD', 'isoHD1474@'),
    'database': os.getenv('MYSQLDATABASE', 'smart_loan_system'),
    'autocommit': True,
    'pool_size': 5,
    'pool_reset_session': True
}

# Create global instance
db = Database(db_config)

# Initialize tables when module is imported
create_tables_if_not_exist()