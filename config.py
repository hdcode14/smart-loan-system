import os

class Config:
    # MySQL Configuration - USING ROOT USER:
    MYSQL_HOST = 'localhost'              # ← Keep as 'localhost'
    MYSQL_USER = 'root'                   # ← CHANGED to 'root'
    MYSQL_PASSWORD = 'isoHD1474@'  # ← YOUR MySQL root password
    MYSQL_DB = 'smart_loan_system'        # ← The database we created
    MYSQL_PORT = 3306                     # ← Default MySQL port
    
    # Flask Configuration
    SECRET_KEY = 'dev-secret-key-change-in-production-2024'
    DEBUG = True
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 604800