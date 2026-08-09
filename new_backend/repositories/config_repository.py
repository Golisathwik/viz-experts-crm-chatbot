"""
Configuration Repository
------------------------
Handles API key storage and retrieval.
"""

import os
from cryptography.fernet import Fernet

from new_backend.database.connection import get_db_connection


# ==========================================================
# Encryption Key
# ==========================================================

KEY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".encryption_key"
)


def get_encryption_key() -> bytes:

    if os.path.exists(KEY_FILE):

        with open(KEY_FILE, "rb") as file:
            return file.read().strip()

    key = Fernet.generate_key()

    with open(KEY_FILE, "wb") as file:
        file.write(key)

    return key


def encrypt_key(plain_text: str) -> str:

    if not plain_text:
        return ""

    key = get_encryption_key()

    fernet = Fernet(key)

    return fernet.encrypt(
        plain_text.encode("utf-8")
    ).decode("utf-8")


def decrypt_key(cipher_text: str) -> str:

    if not cipher_text:
        return ""

    try:

        key = get_encryption_key()

        fernet = Fernet(key)

        return fernet.decrypt(
            cipher_text.encode("utf-8")
        ).decode("utf-8")

    except Exception:

        return cipher_text


# ==========================================================
# Repository
# ==========================================================

class ConfigRepository:

    @staticmethod
    def get_config(user_id: int):

        conn = get_db_connection()

        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT *
            FROM configurations
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        conn.close()

        if not row:
            return None

        config = dict(row)

        config["zoho_api_key"] = decrypt_key(
            config.get("zoho_api_key") or ""
        )

        config["groq_api_key"] = decrypt_key(
            config.get("groq_api_key") or ""
        )

        config["gemini_api_key"] = decrypt_key(
            config.get("gemini_api_key") or ""
        )

        return config

    @staticmethod
    def save_config(
        user_id: int,
        zoho_api_key=None,
        groq_api_key=None,
        gemini_api_key=None
    ):

        current = ConfigRepository.get_config(user_id)

        zoho = zoho_api_key.strip() if zoho_api_key else ""
        groq = groq_api_key.strip() if groq_api_key else ""
        gemini = gemini_api_key.strip() if gemini_api_key else ""

        final_zoho = zoho if zoho else (
            current.get("zoho_api_key") if current else ""
        )

        final_groq = groq if groq else (
            current.get("groq_api_key") if current else ""
        )

        final_gemini = gemini if gemini else (
            current.get("gemini_api_key") if current else ""
        )

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO configurations
            (
                user_id,
                zoho_api_key,
                groq_api_key,
                gemini_api_key
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                encrypt_key(final_zoho),
                encrypt_key(final_groq),
                encrypt_key(final_gemini)
            )
        )

        conn.commit()

        conn.close()