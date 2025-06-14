import sqlite3
from .base import Command
from wordwise.registry import register_command
from wordwise.data.database import get_connection


@register_command
class DeleteCommand(Command):
    # Class-level variable to store the last deleted word's data
    last_deleted_word = None

    @property
    def name(self):
        return "delete"

    @property
    def description(self):
        return "Delete one or more saved words from the database, with undo capability"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "words",
            nargs="*",  # Changed from "+" to "*" to be optional when --undo is used
            help="One or more words to delete from the saved words database"
        )
        group.add_argument(
            "--undo",
            action="store_true",
            help="Restore the most recently deleted word"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt and delete words immediately"
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

            # Handle undo operation
            if args.undo:
                self.handle_undo(conn, cursor)
                return

            # Ensure we have words to delete
            if not args.words:
                print("Please specify one or more words to delete, or use --undo to restore the last deleted word.")
                return

            # Process each word for deletion
            for word in args.words:
                # Check if the word exists in database (case-insensitive)
                cursor.execute(
                    "SELECT * FROM words WHERE LOWER(word) = LOWER(?)",
                    (word,)
                )
                result = cursor.fetchone()

                if not result:
                    print(f"Word '{word}' not found in saved words.")
                    continue

                # Get the exact word with correct case for display
                exact_word = result["word"]

                # Determine whether to delete based on --force flag or confirmation
                proceed_with_deletion = False

                if args.force:
                    # Skip confirmation if --force is specified
                    proceed_with_deletion = True
                else:
                    # Ask for confirmation
                    confirmation = input(f"Are you sure you want to delete '{exact_word}'? (y/n): ")
                    proceed_with_deletion = confirmation.lower() in ["y", "yes"]

                if proceed_with_deletion:
                    # Store the word's data for potential undo
                    self.store_for_undo(dict(result))

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

    def store_for_undo(self, word_data):
        """Store the deleted word's data for potential undo."""
        # If multiple words are deleted in sequence, only the last one can be undone
        DeleteCommand.last_deleted_word = word_data

    def handle_undo(self, conn, cursor):
        """Handle the undo operation to restore the last deleted word."""
        if not DeleteCommand.last_deleted_word:
            print("No deletions to undo.")
            return

        try:
            # Get the stored word data
            word_data = DeleteCommand.last_deleted_word

            # Check if the word already exists (might have been re-added)
            cursor.execute(
                "SELECT word FROM words WHERE LOWER(word) = LOWER(?)",
                (word_data["word"],)
            )
            if cursor.fetchone():
                print(f"Cannot undo deletion: Word '{word_data['word']}' already exists in the database.")
                return

            # Extract all columns except 'id' which might be auto-incremented
            columns = [col for col in word_data.keys() if col != 'id']
            placeholders = ', '.join(['?'] * len(columns))
            column_names = ', '.join(columns)

            # Prepare the values in the same order as columns
            values = [word_data[col] for col in columns]

            # Insert the word back into the database
            cursor.execute(
                f"INSERT INTO words ({column_names}) VALUES ({placeholders})",
                values
            )
            conn.commit()

            print(f"Restored word '{word_data['word']}' to the database.")

            # Clear the undo buffer after successful restoration
            DeleteCommand.last_deleted_word = None

        except sqlite3.Error as e:
            print(f"Error during undo operation: {e}")
            conn.rollback()