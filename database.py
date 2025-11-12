import mysql.connector
from mysql.connector import Error
import logging

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
            cursor = connection.cursor(buffered=True)  # Add buffered=True
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
            cursor = connection.cursor(buffered=True, dictionary=True)  # Add buffered=True
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
            cursor = connection.cursor(buffered=True, dictionary=True)  # Add buffered=True
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
        except Error as e:
            logger.error(f"Fetch all error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'isoHD1474@',  # Your password
    'database': 'smart_loan_system',
    'autocommit': True,  # Add this
    'pool_size': 5,      # Add connection pooling
    'pool_reset_session': True
}

# Create global instance
db = Database(db_config)