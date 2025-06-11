"""
Implementation of the 'edit' command for WordWise CLI that allows updating notes
for saved words in the SQLite database.
"""
import os
import sqlite3

from .base import Command
from ..data.database import get_connection
from wordwise.registry import register_command


@register_command
class EditCommand(Command):
    """Command to edit notes for saved words."""

    @property
    def name(self):
        """Return the command name."""
        return "edit"

    @property
    def description(self):
        """Return the command description."""
        return "Update the note and/or learning status for a saved word"

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "word",
            help="The word to update"
        )
        parser.add_argument(
            "--note",
            help="New note for the word"
        )
        parser.add_argument(
            "--status",
            choices=["to-review", "learned"],
            help="New learning status for the word ('to-review' or 'learned')"
        )

    def execute(self, args):
        """Execute the edit command."""

        # Check if at least one update field is provided
        if args.note is None and args.status is None:
            print("No update fields provided.")
            return
        # Create database directory if it doesn't exist
        conn = get_connection()
        cursor = conn.cursor()

        # Check if the word exists (case-insensitive)
        cursor.execute('SELECT word FROM words WHERE word COLLATE NOCASE = ?', (args.word,))
        existing_word_row = cursor.fetchone()

        if not existing_word_row:
            print(f"The word '{args.word}' was not found in your vocabulary database.")
            conn.close()
            return

        # Get the actual word with its original case for updating and messaging
        existing_word = existing_word_row[0]

        # Build the update query and parameters based on which fields to update
        update_fields = []
        update_params = []
        update_desc = []

        if args.note is not None:
            update_fields.append("note = ?")
            update_params.append(args.note)
            update_desc.append("note")

        if args.status is not None:
            update_fields.append("status = ?")
            update_params.append(args.status)
            update_desc.append("status")

        # Add the word to the params list for the WHERE clause
        update_params.append(existing_word)

        # Update the word in the database
        try:
            query = f"UPDATE words SET {', '.join(update_fields)} WHERE word = ?"
            cursor.execute(query, update_params)
            conn.commit()

            # Build a descriptive success message
            if len(update_desc) == 1:
                print(f"{update_desc[0].capitalize()} updated for '{existing_word}'.")
            else:
                print(f"{' and '.join(update_desc).capitalize()} updated for '{existing_word}'.")

        except sqlite3.Error as e:
            print(f"Error updating '{existing_word}': {e}")
        finally:
            conn.close()