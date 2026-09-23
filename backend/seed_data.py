"""Database connection and lifecycle manager.

Provides dual-engine compatibility for SQLite (local development) and
PostgreSQL (Render managed database), including dynamic schema initialization,
connection pooling context management, and row-dict mapping.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Any, Dict, List, Optional
from backend.config import settings

# Determine database engine from DATABASE_URL
DB_URL = settings.DATABASE_URL
IS_POSTGRES = DB_URL.startswith("postgresql://") or DB_URL.startswith("postgres://")

if IS_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor


class UnifiedCursor:
    """Cursor wrapper that transparently adapts parameter placeholders between
    SQLite ('?') and PostgreSQL ('%s') and returns row dictionaries.
    """

    def __init__(self, raw_cursor, is_postgres: bool):
        self._cursor = raw_cursor
        self._is_postgres = is_postgres

    def execute(self, query: str, params: Optional[tuple] = None):
        if self._is_postgres:
            if "?" in query and "%s" not in query:
                query = query.replace("?", "%s")
            return self._cursor.execute(query, params or ())
        else:
            if "%s" in query and "?" not in query:
                query = query.replace("%s", "?")
            return self._cursor.execute(query, params or ())

    def executemany(self, query: str, seq_of_params):
        if self._is_postgres:
            if "?" in query and "%s" not in query:
                query = query.replace("?", "%s")
            return self._cursor.executemany(query, seq_of_params)
        else:
            if "%s" in query and "?" not in query:
                query = query.replace("%s", "?")
            return self._cursor.executemany(query, seq_of_params)

    def fetchone(self) -> Optional[Dict[str, Any]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self) -> List[Dict[str, Any]]:
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        if self._is_postgres:
            return getattr(self._cursor, "lastrowid", None)
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class UnifiedConnection:
    """Connection wrapper ensuring uniform commit, rollback, and cursor operations."""

    def __init__(self, raw_connection, is_postgres: bool):
        self._connection = raw_connection
        self._is_postgres = is_postgres

    def cursor(self) -> UnifiedCursor:
        if self._is_postgres:
            return UnifiedCursor(self._connection.cursor(cursor_factory=RealDictCursor), is_postgres=True)
        return UnifiedCursor(self._connection.cursor(), is_postgres=False)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def get_raw_connection() -> UnifiedConnection:
    """Establishes an active connection to the designated database engine."""
    if IS_POSTGRES:
        url = DB_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        raw_conn = psycopg2.connect(url)
        return UnifiedConnection(raw_conn, is_postgres=True)
    else:
        if DB_URL.startswith("sqlite:///"):
            path = DB_URL.replace("sqlite:///", "")
        else:
            path = settings.DATABASE_PATH

        raw_conn = sqlite3.connect(path, timeout=15.0)
        raw_conn.execute("PRAGMA journal_mode=WAL;")
        raw_conn.execute("PRAGMA synchronous=NORMAL;")
        raw_conn.execute("PRAGMA foreign_keys=ON;")
        raw_conn.row_factory = sqlite3.Row
        return UnifiedConnection(raw_conn, is_postgres=False)


def init_db() -> None:
    """Initializes tables and indexes, executing each DDL statement individually."""
    with get_db() as conn:
        cursor = conn.cursor()

        if IS_POSTGRES:
            statements = [
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'superadmin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(50) UNIQUE NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    semester INT CHECK (semester BETWEEN 1 AND 8),
                    phone_verified SMALLINT DEFAULT 0 CHECK (phone_verified IN (0, 1)),
                    email_verified SMALLINT DEFAULT 0 CHECK (email_verified IN (0, 1)),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                "CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);",
                "CREATE INDEX IF NOT EXISTS idx_students_phone ON students(phone);",
                "CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);"
            ]
        else:
            statements = [
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'superadmin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT UNIQUE NOT NULL,
                    department TEXT NOT NULL,
                    semester INTEGER CHECK (semester BETWEEN 1 AND 8),
                    phone_verified INTEGER DEFAULT 0 CHECK (phone_verified IN (0, 1)),
                    email_verified INTEGER DEFAULT 0 CHECK (email_verified IN (0, 1)),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """,
                "CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);",
                "CREATE INDEX IF NOT EXISTS idx_students_phone ON students(phone);",
                "CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);"
            ]

        for stmt in statements:
            cursor.execute(stmt.strip())

        conn.commit()


@contextmanager
def get_db() -> Generator[UnifiedConnection, None, None]:
    """Context manager for obtaining a database connection with auto-rollback on error."""
    connection = get_raw_connection()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
