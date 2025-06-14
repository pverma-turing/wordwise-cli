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
            "--undo-count",
            type=int,
            metavar="N",
            help="Number of recent deletions to undo (default: 1)"
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

                buffer = json.loads(content)

                # Safety check - ensure buffer is a list
                if not isinstance(buffer, list):
                    print("Warning: Invalid undo buffer format (not a list). Starting with empty buffer.")
                    return []

                return buffer
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
                # Determine how many entries to undo
                undo_count = args.undo_count if args.undo_count is not None else 1
                if undo_count <= 0:
                    print("Invalid undo count. Please specify a positive number.")
                    return

                self.handle_batch_undo(conn, cursor, undo_count)
                return

            # Handle --undo-count specified without --undo flag
            if args.undo_count is not None and not args.undo:
                print("--undo-count must be used with --undo flag.")
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

            # Apply size management to limit buffer growth (max 100 entries)
            self.prune_undo_buffer(undo_buffer)

            # Save updated buffer
            self.save_undo_buffer(undo_buffer)
        except Exception as e:
            print(f"Warning: Could not store word for undo: {e}")

    def prune_undo_buffer(self, undo_buffer):
        """Limit the undo buffer to the most recent 100 entries."""
        MAX_BUFFER_SIZE = 100

        # If buffer exceeds maximum size, keep only the most recent entries
        if len(undo_buffer) > MAX_BUFFER_SIZE:
            # Keep the most recent MAX_BUFFER_SIZE entries (newest are at the end)
            del undo_buffer[0:len(undo_buffer) - MAX_BUFFER_SIZE]

    def handle_batch_undo(self, conn, cursor, count):
        """Handle batch undo operation to restore multiple deleted words."""
        # Load undo buffer
        undo_buffer = self.load_undo_buffer()

        # Check if undo buffer is empty
        if not undo_buffer:
            print("No deletions to undo.")
            return

        # Determine how many entries we can actually restore
        entries_to_restore = min(count, len(undo_buffer))

        if entries_to_restore < count:
            print(
                f"Note: Only {entries_to_restore} deletion{'' if entries_to_restore == 1 else 's'} available to undo.")

        # Get the current database schema (table columns) - do this once for efficiency
        cursor.execute("PRAGMA table_info(words)")
        current_schema = {row[1] for row in cursor.fetchall()}  # Set of column names

        # Track statistics
        restored_count = 0
        skipped_count = 0

        try:
            # Process each word to restore, one at a time
            for i in range(entries_to_restore):
                # Stop if we've run out of entries
                if not undo_buffer:
                    break

                # Get the most recent (last) entry in the buffer
                word_data = undo_buffer[-1]  # Access but don't remove the last item yet
                exact_word = word_data["word"]

                # Attempt to restore this word
                result = self.restore_word(conn, cursor, undo_buffer, current_schema)

                if result == "restored":
                    restored_count += 1
                elif result == "skipped":
                    skipped_count += 1
                elif result == "schema_mismatch":
                    # Stop the entire batch operation if we hit a schema mismatch
                    print(f"Batch undo operation stopped after restoring {restored_count} " +
                          f"word{'' if restored_count == 1 else 's'} due to schema mismatch.")
                    return

            # Save the final state of the undo buffer
            self.save_undo_buffer(undo_buffer)

            # Provide summary of the operation
            if restored_count > 0:
                print(f"Successfully restored {restored_count} word{'' if restored_count == 1 else 's'}.")

            if skipped_count > 0:
                print(
                    f"Skipped {skipped_count} word{'' if skipped_count == 1 else 's'} that already exist in the database.")

            # Let the user know if more words can be restored
            if undo_buffer:
                remaining_count = len(undo_buffer)
                print(f"{remaining_count} more deletion{'' if remaining_count == 1 else 's'} can be undone.")

        except sqlite3.Error as e:
            print(f"Database error during batch undo operation: {e}")
            conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred during batch undo: {e}")

    def restore_word(self, conn, cursor, undo_buffer, current_schema=None):
        """Restore a single word from the undo buffer. Returns status: 'restored', 'skipped', or 'schema_mismatch'."""
        try:
            # Return early if buffer is empty
            if not undo_buffer:
                return "empty_buffer"

            # Get the most recent (last) entry in the buffer
            word_data = undo_buffer[-1]  # Access but don't remove the last item yet

            # Check if the word already exists (might have been re-added)
            cursor.execute(
                "SELECT word FROM words WHERE LOWER(word) = LOWER(?)",
                (word_data["word"],)
            )
            if cursor.fetchone():
                print(f"Skipped: Word '{word_data['word']}' already exists in the database.")
                # Remove the entry we tried to restore
                undo_buffer.pop()
                return "skipped"

            # Get schema if not provided
            if current_schema is None:
                cursor.execute("PRAGMA table_info(words)")
                current_schema = {row[1] for row in cursor.fetchall()}  # Set of column names

            # Extract fields from word_data (excluding 'id')
            word_fields = {col for col in word_data.keys() if col != 'id'}

            # Check if all fields in word_data exist in the current schema
            missing_fields = word_fields - current_schema
            if missing_fields:
                print(f"Undo failed for '{word_data['word']}': schema mismatch detected.")
                print(
                    f"The following fields are not present in the current database schema: {', '.join(missing_fields)}")
                return "schema_mismatch"  # Don't modify the undo buffer

            # Now we can safely remove the item from the buffer
            word_data = undo_buffer.pop()

            # Extract fields that exist in both the word data and current schema
            valid_columns = [col for col in word_data.keys() if col != 'id' and col in current_schema]
            placeholders = ', '.join(['?'] * len(valid_columns))
            column_names = ', '.join(valid_columns)

            # Prepare the values in the same order as columns
            values = [word_data[col] for col in valid_columns]

            # Insert the word back into the database
            cursor.execute(
                f"INSERT INTO words ({column_names}) VALUES ({placeholders})",
                values
            )
            conn.commit()

            print(f"Restored word '{word_data['word']}' to the database.")
            return "restored"

        except sqlite3.Error as e:
            print(f"Error during word restoration: {e}")
            conn.rollback()
            return "error"
        except Exception as e:
            print(f"An unexpected error occurred during word restoration: {e}")
            return "error"