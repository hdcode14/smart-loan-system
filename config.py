import os

class Config:
    # MySQL Configuration - USING RAILWAY ENVIRONMENT VARIABLES
    MYSQL_HOST = os.getenv('MYSQLHOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQLUSER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQLPASSWORD', 'isoHD1474@')
    MYSQL_DB = os.getenv('MYSQLDATABASE', 'smart_loan_system')
    MYSQL_PORT = int(os.getenv('MYSQLPORT', 3306))
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production-2024')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 604800