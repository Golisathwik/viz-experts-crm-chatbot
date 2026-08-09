from new_backend.database.connection import get_db_connection
from typing import Optional


class ChatSessionRepository:
    
    @staticmethod
    def update_chat_session_active_context(session_id: int, active_module: Optional[str], active_record_id: Optional[str], active_record_name: Optional[str], last_action: Optional[str] = None):
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if last_action is not None:
                cursor.execute(
                    """
                    UPDATE chat_sessions 
                    SET active_module = ?, active_record_id = ?, active_record_name = ?, last_action = ?
                    WHERE id = ?
                    """,
                    (active_module, active_record_id, active_record_name, last_action, session_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE chat_sessions 
                    SET active_module = ?, active_record_id = ?, active_record_name = ?
                    WHERE id = ?
                    """,
                    (active_module, active_record_id, active_record_name, session_id)
                )
            conn.commit()
            conn.close()
        
        except Exception as e:
            conn.close()
            raise e
    
    @staticmethod
    def get_chat_session_active_context(session_id: int) -> dict:
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            row = cursor.execute(
                "SELECT active_module, active_record_id, active_record_name, last_action FROM chat_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            conn.close()
            res = {
                "active_module": row["active_module"] if row else None,
                "active_record_id": row["active_record_id"] if row else None,
                "active_record_name": row["active_record_name"] if row else None,
                "last_action": row["last_action"] if row else None
            }
            return res
        except Exception as e:
            conn.close()
            raise e