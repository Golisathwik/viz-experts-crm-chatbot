"""
User Repository
---------------
Handles all database operations related to users.
"""

import sqlite3
from typing import Optional

from new_backend.database.connection import get_db_connection


class UserRepository:

    @staticmethod
    def create_user(full_name: str, email: str, password_hash: str) -> Optional[int]:

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users
                (full_name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (
                    full_name,
                    email.lower().strip(),
                    password_hash
                )
            )

            conn.commit()

            return cursor.lastrowid

        except sqlite3.IntegrityError:
            return None

        finally:
            conn.close()

    @staticmethod
    def get_user_by_email(email: str):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email.lower().strip(),)
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    @staticmethod
    def get_user_by_id(user_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    @staticmethod
    def update_user_password(
        user_id: int,
        password_hash: str
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (
                password_hash,
                user_id
            )
        )

        conn.commit()

        conn.close()