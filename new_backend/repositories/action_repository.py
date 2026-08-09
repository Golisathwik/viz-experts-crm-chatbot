"""
Action Repository
-----------------
Handles pending actions and audit logs.
"""

from datetime import datetime
from typing import Optional

from new_backend.database.connection import get_db_connection


class ActionRepository:

    # ==========================================================
    # Pending Actions
    # ==========================================================

    @staticmethod
    def create_pending_action(
        session_id: int,
        action_type: str,
        module: str,
        record_id: str,
        record_name: str,
        field_name: str = None,
        old_value: str = None,
        new_value: str = None,
        status: str = "PENDING"
    ) -> int:

        conn = get_db_connection()
        cursor = conn.cursor()

        # Close previous active actions
        cursor.execute(
            """
            UPDATE pending_actions
            SET
                status='FAILED',
                last_updated_at=CURRENT_TIMESTAMP
            WHERE
                session_id=?
                AND status NOT IN ('COMPLETED','FAILED')
            """,
            (session_id,)
        )

        cursor.execute(
            """
            INSERT INTO pending_actions
            (
                session_id,
                action_type,
                module,
                record_id,
                record_name,
                field_name,
                old_value,
                new_value,
                status,
                created_at,
                last_updated_at
            )
            VALUES
            (
                ?,?,?,?,?,?,?,?,?,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """,
            (
                session_id,
                action_type,
                module,
                record_id,
                record_name,
                field_name,
                old_value,
                new_value,
                status
            )
        )

        conn.commit()

        action_id = cursor.lastrowid

        conn.close()

        return action_id

    @staticmethod
    def update_pending_action(
        action_id: int,
        **kwargs
    ):

        if not kwargs:
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        set_clause = ", ".join(
            [f"{key}=?" for key in kwargs.keys()]
        )

        values = list(kwargs.values())

        cursor.execute(
            f"""
            UPDATE pending_actions
            SET
                {set_clause},
                last_updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            values + [action_id]
        )

        conn.commit()

        conn.close()

    @staticmethod
    def get_active_pending_action(
        session_id: int
    ) -> Optional[dict]:

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM pending_actions
            WHERE
                session_id=?
                AND status NOT IN ('COMPLETED','FAILED')
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,)
        ).fetchone()

        if not row:
            conn.close()
            return None

        action = dict(row)

        expired = cursor.execute(
            """
            SELECT
            (julianday('now')-julianday(?))*1440 AS diff
            """,
            (action["last_updated_at"],)
        ).fetchone()

        if expired and expired["diff"] > 30:

            cursor.execute(
                """
                UPDATE pending_actions
                SET
                    status='FAILED',
                    last_updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (action["id"],)
            )

            conn.commit()

            action["status"] = "FAILED"

            action["expired"] = True

        else:

            action["expired"] = False

        conn.close()

        return action

    # ==========================================================
    # Audit Logs
    # ==========================================================

    @staticmethod
    def log_update_audit(
        session_id: int,
        action_type: str,
        module: str,
        record_id: str,
        record_name: str,
        field_name: str,
        old_value: str,
        new_value: str,
        user_id=None,
        status=None,
        verification_result=None
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audit_logs
            (
                session_id,
                action_type,
                module,
                record_id,
                record_name,
                field_name,
                old_value,
                new_value,
                user_id,
                status,
                verification_result,
                executed_at
            )
            VALUES
            (
                ?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP
            )
            """,
            (
                session_id,
                action_type,
                module,
                record_id,
                record_name,
                field_name,
                old_value,
                new_value,
                user_id,
                status,
                verification_result
            )
        )

        conn.commit()

        conn.close()