"""Database module for WordWise persistence."""

import os
import sqlite3
from datetime import datetime

# Store database in user's home directory
DB_PATH = os.path.expanduser(".wordwise.db")


def get_connection():
    """
    Establish and return a connection to the SQLite database.
    Creates the database file if it doesn't exist.

    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_database():
    """
    Initialize the database with required tables and columns.
    Creates new tables if they don't exist and adds new columns to existing tables
    for backward compatibility.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create words table if it doesn't exist with original columns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS words (
        word TEXT PRIMARY KEY,
        note TEXT,
        date_added TEXT,
        status TEXT DEFAULT 'to-review'
    )
    """)

    # Check if the columns for spaced repetition exist, add them if they don't
    # This ensures backward compatibility with existing databases

    # Get the current columns in the words table
    cursor.execute("PRAGMA table_info(words)")
    columns = [column[1] for column in cursor.fetchall()]

    # Add review_interval column if it doesn't exist
    if 'review_interval' not in columns:
        cursor.execute("ALTER TABLE words ADD COLUMN review_interval INTEGER")

    # Add last_review_date column if it doesn't exist
    if 'last_review_date' not in columns:
        cursor.execute("ALTER TABLE words ADD COLUMN last_review_date TEXT")

    # Add next_review_date column if it doesn't exist
    if 'next_review_date' not in columns:
        cursor.execute("ALTER TABLE words ADD COLUMN next_review_date TEXT")

    # Add last_review_result column if it doesn't exist (for backward compatibility with review command)
    if 'last_review_result' not in columns:
        cursor.execute("ALTER TABLE words ADD COLUMN last_review_result TEXT")

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

        # Check if the word already exists (case-insensitive)
        cursor.execute('SELECT word FROM words WHERE word COLLATE NOCASE = ?', (word,))
        existing_word = cursor.fetchone()

        if existing_word:
            print(f"The word '{word}' is already saved.")
            conn.close()
            return

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