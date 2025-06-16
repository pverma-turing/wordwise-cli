import sqlite3
from datetime import datetime, timedelta


class SchedulingService:
    """
    Service for managing spaced repetition scheduling operations.
    Handles updating and initializing scheduling fields for words.
    """

    @staticmethod
    def update_scheduling(cursor, word, recall_correct, max_interval=60):
        """
        Update spaced repetition scheduling parameters for a word after review.
        Handles backward compatibility with records that may have NULL values
        for the spaced repetition fields.

        Args:
            cursor: Database cursor
            word: The word that was reviewed
            recall_correct: Boolean indicating if the user recalled the word correctly
            max_interval: Maximum review interval in days (default: 60)
        """
        try:
            # Get the current review_interval
            cursor.execute("SELECT review_interval FROM words WHERE word = ?", (word,))
            result = cursor.fetchone()

            # Handle case where review_interval might be NULL/None or record doesn't exist
            if not result or result[0] is None:
                # For backward compatibility, use default value 1
                current_interval = 1
            else:
                current_interval = result[0]

            # Update interval based on recall result
            if recall_correct:
                # Double the interval for correct recalls
                new_interval = current_interval * 2
            else:
                # Reset to minimum for incorrect recalls
                new_interval = 1

            # Apply min/max caps using the configurable max_interval
            new_interval = max(1, min(new_interval, max_interval))

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
                       next_review_date = ?
                   WHERE word = ?""",
                (new_interval, today_iso, next_review_iso, word)
            )
        except Exception as e:
            # Log the error but don't disrupt the review flow
            print(f"Error updating scheduling for '{word}': {e}")

    @staticmethod
    def initialize_missing_fields(cursor):
        """
        Initialize spaced repetition scheduling fields for legacy records.
        Finds all records with NULL scheduling fields and sets them to default values.

        Args:
            cursor: Database cursor

        Returns:
            int: Number of records initialized
        """
        try:
            # Calculate today's date
            today = datetime.now()
            today_iso = today.isoformat()

            # Find all records with missing scheduling data
            cursor.execute("""
                SELECT word FROM words 
                WHERE review_interval IS NULL 
                   OR last_review_date IS NULL 
                   OR next_review_date IS NULL
            """)
            legacy_words = [row[0] for row in cursor.fetchall()]

            if not legacy_words:
                return 0  # No legacy records to update

            # Update all legacy records with default values
            initialized_count = 0
            for word in legacy_words:
                cursor.execute("""
                    UPDATE words
                    SET review_interval = 1,
                        last_review_date = ?,
                        next_review_date = ?
                    WHERE word = ?
                """, (today_iso, today_iso, word))
                initialized_count += cursor.rowcount

            return initialized_count

        except Exception as e:
            # Log the error but allow the review command to continue
            print(f"Error initializing scheduling fields: {e}")
            return 0