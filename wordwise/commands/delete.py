import json
import os
import sqlite3
from pathlib import Path

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

    def get_undo_buffer_path(self):
        """Get the path to the undo buffer JSON file (in the same directory as the database)."""
        # Get database directory (same as wordwise.db)
        buffer_path = "undo_buffer.json"
        return buffer_path

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
        except json.JSONDecodeError:
            print("Error processing undo buffer file.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()

    def store_for_undo(self, word_data):
        """Store the deleted word's data to JSON file for potential undo."""
        try:
            # Convert SQLite Row type values to JSON serializable format
            serializable_data = {}
            for key, value in word_data.items():
                # Convert non-JSON serializable types if needed
                serializable_data[key] = value

            # Write the data to the JSON file
            buffer_path = self.get_undo_buffer_path()
            with open(buffer_path, 'w') as f:
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not store word for undo: {e}")

    def handle_undo(self, conn, cursor):
        """Handle the undo operation to restore the last deleted word from JSON file."""
        buffer_path = self.get_undo_buffer_path()

        # Check if undo buffer file exists
        if not os.path.exists(buffer_path) or os.path.getsize(buffer_path) == 0:
            print("No deletions to undo.")
            return

        try:
            # Load the stored word data from the JSON file
            with open(buffer_path, 'r') as f:
                word_data = json.load(f)

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

            # Clear the undo buffer file after successful restoration
            self.clear_undo_buffer()

        except sqlite3.Error as e:
            print(f"Error during undo operation: {e}")
            conn.rollback()
        except json.JSONDecodeError:
            print("Error reading undo buffer: Invalid JSON format.")
            # Clear the invalid buffer
            self.clear_undo_buffer()
        except Exception as e:
            print(f"An unexpected error occurred during undo: {e}")

    def clear_undo_buffer(self):
        """Clear the undo buffer file."""
        try:
            buffer_path = self.get_undo_buffer_path()
            # Simply truncate the file by opening it in write mode
            with open(buffer_path, 'w') as f:
                f.write("")
        except Exception as e:
            print(f"Warning: Could not clear undo buffer: {e}")