import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._connect()

    def _connect(self):
        """Connect to the database"""
        try:
            database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres_password@localhost:5432/appointment_chatbot')
            self.engine = create_engine(database_url, pool_pre_ping=True)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def is_connected(self):
        """Check if database is connected"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_session(self):
        """Get database session"""
        return self.SessionLocal()

    def execute_query(self, query, params=None):
        """Execute a raw SQL query"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error(f"Database query error: {e}")
            raise
