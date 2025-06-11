"""Database module for WordWise persistence."""

import os
import sqlite3
from datetime import datetime

# Store database in user's home directory
DB_PATH = os.path.expanduser(".wordwise.db")


def get_connection():
    """
    Get a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_database():
    """Initialize the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create the words table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY,
        word TEXT UNIQUE NOT NULL,
        note TEXT,
        date_added TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()


def save_word(word, note=None):
    """
    Save a word to the database.

    Args:
        word (str): Word to save
        note (str, optional): User-provided note

    Returns:
        bool: True if successful, False if word already exists
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get current date in ISO format (YYYY-MM-DD)
        today = datetime.now().strftime("%Y-%m-%d")

        # Insert the word
        cursor.execute(
            "INSERT INTO words (word, note, date_added, status) VALUES (?, ?, ?, ?)",
            (word, note, today, "to-review")
        )

        conn.commit()
        conn.close()
        return True

    except sqlite3.IntegrityError:
        # Word already exists (due to UNIQUE constraint)
        return False


# Initialize database when module is imported
init_database()