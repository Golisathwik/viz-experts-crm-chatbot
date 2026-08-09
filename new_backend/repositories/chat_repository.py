"""
Chat Repository
---------------
Handles chat sessions and chat messages.
"""

from new_backend.database.connection import get_db_connection


class ChatRepository:

    # ==========================================================
    # Chat Sessions
    # ==========================================================

    @staticmethod
    def create_chat_session(user_id: int, title: str):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO chat_sessions
            (user_id, title)
            VALUES (?, ?)
            """,
            (
                user_id,
                title.strip()
            )
        )

        conn.commit()

        session_id = cursor.lastrowid

        conn.close()

        return session_id

    @staticmethod
    def get_chat_sessions(user_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        rows = cursor.execute(
            """
            SELECT *
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()

        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def get_chat_session(session_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM chat_sessions
            WHERE id = ?
            """,
            (session_id,)
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    @staticmethod
    def delete_chat_session(session_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM chat_sessions
            WHERE id = ?
            """,
            (session_id,)
        )

        conn.commit()

        conn.close()

    @staticmethod
    def delete_all_chat_sessions(user_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM chat_sessions
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.commit()

        conn.close()

    # ==========================================================
    # Chat Messages
    # ==========================================================

    @staticmethod
    def save_chat_message(
        session_id: int,
        role: str,
        message: str,
        response_json: str = None,
    ):

        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == "user":
            session = cursor.execute(
                """
                SELECT title
                FROM chat_sessions
                WHERE id = ?
                """,
                (session_id,)
            ).fetchone()

            if session and session["title"] == "New Chat":

                title = message.strip()

                if len(title) > 60:
                    title = title[:57] + "..."

                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET title = ?
                    WHERE id = ?
                    """,
                    (
                        title,
                        session_id
                    )
                )

        cursor.execute(
            """
            INSERT INTO chat_messages
            (
                session_id,
                role,
                message,
                response_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                message,
                response_json
            )
        )

        conn.commit()

        message_id = cursor.lastrowid

        conn.close()

        return message_id

    @staticmethod
    def get_chat_messages(session_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        rows = cursor.execute(
            """
            SELECT *
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,)
        ).fetchall()

        conn.close()

        return [dict(row) for row in rows]

    # ==========================================================
    # Active Context
    # ==========================================================

    @staticmethod
    def update_active_context(
        session_id: int,
        active_module=None,
        active_record_id=None,
        active_record_name=None,
        last_action=None
    ):

        conn = get_db_connection()
        cursor = conn.cursor()

        if last_action is not None:

            cursor.execute(
                """
                UPDATE chat_sessions
                SET
                    active_module=?,
                    active_record_id=?,
                    active_record_name=?,
                    last_action=?
                WHERE id=?
                """,
                (
                    active_module,
                    active_record_id,
                    active_record_name,
                    last_action,
                    session_id
                )
            )

        else:

            cursor.execute(
                """
                UPDATE chat_sessions
                SET
                    active_module=?,
                    active_record_id=?,
                    active_record_name=?
                WHERE id=?
                """,
                (
                    active_module,
                    active_record_id,
                    active_record_name,
                    session_id
                )
            )

        conn.commit()

        conn.close()

    @staticmethod
    def get_active_context(session_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT
                active_module,
                active_record_id,
                active_record_name,
                last_action
            FROM chat_sessions
            WHERE id=?
            """,
            (session_id,)
        ).fetchone()

        conn.close()

        if not row:

            return {
                "active_module": None,
                "active_record_id": None,
                "active_record_name": None,
                "last_action": None
            }

        return dict(row)
    
    @staticmethod
    def update_chat_session_title(session_id: int, title: str):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE chat_sessions
            SET title = ?
            WHERE id = ?
            """,
            (
                title.strip(),
                session_id
            )
        )

        conn.commit()
        conn.close()