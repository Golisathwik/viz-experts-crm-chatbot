"""
Zoho OAuth Repository
---------------------
Stores and retrieves employee-specific Zoho OAuth credentials.
"""

from new_backend.database.connection import get_db_connection
from new_backend.repositories.config_repository import (
    encrypt_key,
    decrypt_key,
)


class ZohoOAuthRepository:

    @staticmethod
    def save_connection(
        user_id: int,
        client_id: str,
        client_secret: str,
    ):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO zoho_connections
            (
                user_id,
                client_id,
                client_secret
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                client_id = excluded.client_id,
                client_secret = excluded.client_secret,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                encrypt_key(client_id),
                encrypt_key(client_secret),
            ),
        )

        conn.commit()
        conn.close()

    @staticmethod
    def get_connection(user_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM zoho_connections
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        conn.close()

        if not row:
            return None

        data = dict(row)

        data["client_id"] = decrypt_key(
            data.get("client_id") or ""
        )

        data["client_secret"] = decrypt_key(
            data.get("client_secret") or ""
        )

        data["access_token"] = decrypt_key(
            data.get("access_token") or ""
        )

        data["refresh_token"] = decrypt_key(
            data.get("refresh_token") or ""
        )

        return data

    @staticmethod
    def save_oauth_state(
        state: str,
        user_id: int,
        code_verifier: str,
        expires_at: str,
    ):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO zoho_oauth_states
            (
                state,
                user_id,
                code_verifier,
                expires_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                state,
                user_id,
                code_verifier,
                expires_at,
            ),
        )

        conn.commit()
        conn.close()

    @staticmethod
    def get_oauth_state(state: str):

        conn = get_db_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM zoho_oauth_states
            WHERE state = ?
            """,
            (state,),
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    @staticmethod
    def delete_oauth_state(state: str):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM zoho_oauth_states
            WHERE state = ?
            """,
            (state,),
        )

        conn.commit()
        conn.close()

    @staticmethod
    def update_tokens(
        user_id: int,
        access_token: str,
        refresh_token: str | None = None,
        api_domain: str | None = None,
        token_expires_at: str | None = None,
    ):
        current = ZohoOAuthRepository.get_connection(user_id)

        if not current:
            raise ValueError(
                "Zoho connection not found."
            )

        final_refresh_token = (
            refresh_token
            if refresh_token
            else current.get("refresh_token", "")
        )

        final_api_domain = (
            api_domain
            if api_domain
            else current.get("api_domain", "")
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE zoho_connections
            SET
                access_token = ?,
                refresh_token = ?,
                api_domain = ?,
                token_expires_at = ?,
                connected_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                encrypt_key(access_token),
                encrypt_key(final_refresh_token),
                final_api_domain,
                token_expires_at,
                user_id,
            ),
        )

        conn.commit()
        conn.close()
        
    @staticmethod
    def delete_connection(user_id: int):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM zoho_connections
            WHERE user_id = ?
            """,
            (user_id,),
        )

        conn.commit()
        conn.close()