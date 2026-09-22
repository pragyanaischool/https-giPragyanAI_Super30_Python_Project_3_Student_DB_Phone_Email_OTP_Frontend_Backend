import sqlite3
from contextlib import contextmanager
from typing import Generator
from backend.config import settings


def get_connection() -> sqlite3.Connection:
    """Creates and configures a SQLite connection."""
    conn = sqlite3.connect(
        settings.DATABASE_PATH,
        timeout=10.0,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    # Enable WAL mode for better read/write concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys=ON;")
    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes tables and indexes if they do not already exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Admins Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'superadmin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Students Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
                phone_verified INTEGER NOT NULL DEFAULT 0 CHECK (phone_verified IN (0, 1)),
                email_verified INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Performance Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_students_phone ON students(phone);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_students_department ON students(department);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_students_verification 
            ON students(phone_verified, email_verified);
        """)

        conn.commit()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for managing transactions and connection closing.
    
    Automatically rolls back uncommitted changes if an exception occurs.
    """
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
