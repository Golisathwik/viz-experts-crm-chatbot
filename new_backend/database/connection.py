"""
Database Connection
-------------------
Central SQLite connection manager.
"""

import sqlite3
from new_backend.config.settings import settings


def get_db_connection():
    """
    Returns a SQLite connection with Row factory enabled.
    """
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn