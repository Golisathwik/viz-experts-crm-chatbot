"""
Database Schema
---------------
Creates all database tables.
"""

import sqlite3

from new_backend.database.connection import get_db_connection


def initialize_database():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Configurations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        zoho_api_key TEXT NOT NULL,
        groq_api_key TEXT NOT NULL,
        gemini_api_key TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
        # Zoho OAuth Connections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zoho_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        client_id TEXT NOT NULL,
        client_secret TEXT NOT NULL,
        access_token TEXT,
        refresh_token TEXT,
        api_domain TEXT,
        token_expires_at TIMESTAMP,
        connected_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Chat Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        active_module TEXT,
        active_record_id TEXT,
        active_record_name TEXT,
        last_action TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Chat Messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT CHECK(role IN ('user','assistant')) NOT NULL,
        message TEXT NOT NULL,
        response_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    );
    """)

    # Pending Actions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        action_type TEXT NOT NULL,
        module TEXT,
        record_id TEXT,
        record_name TEXT,
        field_name TEXT,
        old_value TEXT,
        new_value TEXT,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    );
    """)

    # Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        action_type TEXT NOT NULL,
        module TEXT NOT NULL,
        record_id TEXT NOT NULL,
        record_name TEXT NOT NULL,
        field_name TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT NOT NULL,
        user_id INTEGER,
        status TEXT,
        verification_result TEXT,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    );
    """)

    # Provider Health
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS provider_health (
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        success_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        rate_limit_count INTEGER DEFAULT 0,
        consecutive_failures INTEGER DEFAULT 0,
        average_latency REAL DEFAULT 0.0,
        last_success_time TIMESTAMP,
        last_failure_time TIMESTAMP,
        cooldown_until TIMESTAMP,
        current_health_score REAL DEFAULT 100.0,
        PRIMARY KEY(provider, model)
    );
    """)
    
    # Zoho OAuth Connections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zoho_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        client_id TEXT NOT NULL,
        client_secret TEXT NOT NULL,
        access_token TEXT,
        refresh_token TEXT,
        api_domain TEXT,
        token_expires_at TEXT,
        connected_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Zoho OAuth States
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zoho_oauth_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        code_verifier TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()