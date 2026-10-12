"""Database utilities và helper functions"""

from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any

class DatabaseService:
    """Service cho database operations"""

    @staticmethod
    def execute_raw_query(db: Session, query: str, params: Dict = None) -> List[Dict]:
        """
        Thực hiện raw SQL query

        Args:
            db: Database session
            query: SQL query string
            params: Dictionary của parameters

        Returns:
            List of dictionaries
        """
        if params is None:
            params = {}

        result = db.execute(text(query), params)
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]

    @staticmethod
    def execute_raw_scalar(db: Session, query: str, params: Dict = None) -> Any:
        """
        Thực hiện raw SQL query và trả về 1 giá trị

        Args:
            db: Database session
            query: SQL query string
            params: Dictionary của parameters

        Returns:
            Scalar value
        """
        if params is None:
            params = {}

        result = db.execute(text(query), params)
        return result.scalar_one_or_none()

    @staticmethod
    def check_connection(db: Session) -> bool:
        """Kiểm tra kết nối database"""
        try:
            result = db.execute(text("SELECT 1"))
            return result.scalar_one() == 1
        except Exception:
            return False
