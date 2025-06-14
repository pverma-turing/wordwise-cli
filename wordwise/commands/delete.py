import sqlite3
from .base import Command
from wordwise.registry import register_command
from wordwise.data.database import get_connection


@register_command
class DeleteCommand(Command):
    @property
    def name(self):
        return "delete"

    @property
    def description(self):
        return "Delete one or more saved words from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "words",
            nargs="+",
            help="One or more words to delete from the saved words database"
        )

    def execute(self, args):
        conn = None
        try:
            # Connect to the SQLite database
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if words table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='words'"
            )
            if not cursor.fetchone():
                print("No saved words database found.")
                return

            # Process each word for deletion
            for word in args.words:
                # Check if the word exists in database (case-insensitive)
                cursor.execute(
                    "SELECT word FROM words WHERE LOWER(word) = LOWER(?)",
                    (word,)
                )
                result = cursor.fetchone()

                if not result:
                    print(f"Word '{word}' not found in saved words.")
                    continue

                # Get the exact word with correct case for confirmation
                exact_word = result[0]

                # Ask for confirmation
                confirmation = input(f"Are you sure you want to delete '{exact_word}'? (y/n): ")

                if confirmation.lower() in ["y", "yes"]:
                    # Delete the word
                    cursor.execute(
                        "DELETE FROM words WHERE LOWER(word) = LOWER(?)",
                        (word,)
                    )
                    conn.commit()
                    print(f"Word '{exact_word}' has been deleted.")
                else:
                    print(f"Deletion of '{exact_word}' cancelled.")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()