"""Database module for WordWise persistence."""

import os
import sqlite3
from datetime import timedelta, datetime

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
    Save a word to the database with initial spaced repetition scheduling values.

    Args:
        word (str): The word to save
        note (str, optional): An optional note for the word

    Returns:
        bool: True if word was saved, False if word already exists
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if word already exists
        cursor.execute("SELECT word FROM words WHERE word = ?", (word,))
        if cursor.fetchone():
            conn.close()
            return False

        # Get current date in ISO format
        from datetime import datetime
        current_date = datetime.now().isoformat()

        # Insert new word with spaced repetition fields initialized
        cursor.execute(
            """INSERT INTO words 
               (word, note, date_added, status, review_interval, last_review_date, next_review_date) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (word, note, current_date, "to-review", 1, current_date, current_date)
        )

        conn.commit()
        return True
    except sqlite3.Error as e:
        # Log the error or handle it appropriately
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


def update_word_scheduling(conn, word, is_correct):
    """
    Update spaced repetition scheduling fields for a word after review.

    Args:
        conn (sqlite3.Connection): Database connection
        word (str): The word that was reviewed
        is_correct (bool): Whether the user correctly recalled the word
    """
    cursor = conn.cursor()

    try:
        # First, get the current review_interval (if it exists)
        cursor.execute("SELECT review_interval FROM words WHERE word = ?", (word,))
        result = cursor.fetchone()

        if result is None:
            # Word not found - this should not happen in normal operation
            print(f"Warning: '{word}' not found in database when updating scheduling.")
            return

        current_interval = result[0]
        # Handle None/NULL value for backwards compatibility
        if current_interval is None:
            current_interval = 1

        # Update the review_interval based on recall result
        if is_correct:
            # Double the interval (with a minimum of 1 day)
            new_interval = max(1, current_interval * 2)
        else:
            # Reset to 1 day for incorrect recalls
            new_interval = 1

        # Calculate dates
        today = datetime.now()
        today_iso = today.isoformat()
        next_review = today + timedelta(days=new_interval)
        next_review_iso = next_review.isoformat()

        # Update the word with new scheduling information
        cursor.execute(
            """UPDATE words 
               SET review_interval = ?, 
                   last_review_date = ?, 
                   next_review_date = ?, 
                   last_review_result = ?
               WHERE word = ?""",
            (new_interval, today_iso, next_review_iso,
             "correct" if is_correct else "incorrect", word)
        )

        conn.commit()
    except sqlite3.Error as e:
        # Log the error but don't crash the review session
        print(f"Database error when updating scheduling for '{word}': {e}")
        # Attempt to rollback if needed
        try:
            conn.rollback()
        except:
            pass


# Initialize database when module is imported
init_database()