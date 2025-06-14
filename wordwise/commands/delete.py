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
        return "Delete one or more saved words from the database, with multi-level undo capability"

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

    def load_undo_buffer(self):
        """Load the undo buffer list from the JSON file."""
        buffer_path = self.get_undo_buffer_path()
        if not os.path.exists(buffer_path):
            return []

        try:
            with open(buffer_path, 'r') as f:
                content = f.read().strip()
                if not content:  # Empty file
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            print("Warning: Invalid undo buffer format. Starting with empty buffer.")
            return []
        except Exception as e:
            print(f"Warning: Could not load undo buffer: {e}")
            return []

    def save_undo_buffer(self, buffer_list):
        """Save the undo buffer list to the JSON file."""
        try:
            buffer_path = self.get_undo_buffer_path()
            with open(buffer_path, 'w') as f:
                json.dump(buffer_list, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save undo buffer: {e}")

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

            # Load existing undo buffer
            undo_buffer = self.load_undo_buffer()

            # Append new deleted word to buffer
            undo_buffer.append(serializable_data)

            # Save updated buffer
            self.save_undo_buffer(undo_buffer)
        except Exception as e:
            print(f"Warning: Could not store word for undo: {e}")

    def handle_undo(self, conn, cursor):
        """Handle the undo operation to restore the most recent deleted word from JSON file."""
        # Load undo buffer
        undo_buffer = self.load_undo_buffer()

        # Check if undo buffer is empty
        if not undo_buffer:
            print("No deletions to undo.")
            return

        try:
            # Get the most recent (last) entry in the buffer
            word_data = undo_buffer.pop()  # Remove and return the last item

            # Check if the word already exists (might have been re-added)
            cursor.execute(
                "SELECT word FROM words WHERE LOWER(word) = LOWER(?)",
                (word_data["word"],)
            )
            if cursor.fetchone():
                print(f"Cannot undo deletion: Word '{word_data['word']}' already exists in the database.")
                # Save the updated buffer (without the entry we tried to restore)
                self.save_undo_buffer(undo_buffer)
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

            # Save the updated undo buffer (without the entry we just restored)
            self.save_undo_buffer(undo_buffer)

            # Let the user know if more words can be restored
            if undo_buffer:
                word_count = len(undo_buffer)
                print(f"{word_count} more deletion{'' if word_count == 1 else 's'} can be undone.")

        except sqlite3.Error as e:
            print(f"Error during undo operation: {e}")
            conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred during undo: {e}")