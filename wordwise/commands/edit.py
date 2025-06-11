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
        return "Update the note for a saved word"

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "word",
            help="The word to update"
        )
        parser.add_argument(
            "--note",
            required=True,
            help="New note for the word"
        )

    def execute(self, args):
        """Execute the edit command."""
        # Create database directory if it doesn't exist
        conn = get_connection()
        cursor = conn.cursor()

        # Check if the word exists (case-insensitive)
        cursor.execute('SELECT word FROM words WHERE word COLLATE NOCASE = ?', (args.word,))
        existing_word_row = cursor.fetchone()

        if not existing_word_row:
            print(f"The word '{args.word}' was not found.")
            conn.close()
            return

        # Get the actual word with its original case for updating and messaging
        existing_word = existing_word_row[0]

        # Update the note for the word
        try:
            cursor.execute(
                'UPDATE words SET note = ? WHERE word = ?',
                (args.note, existing_word)
            )
            conn.commit()
            print(f"Note updated for '{existing_word}'.")
        except sqlite3.Error as e:
            print(f"Error updating note for '{existing_word}': {e}")
        finally:
            conn.close()