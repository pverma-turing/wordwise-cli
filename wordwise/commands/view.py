"""
Implementation of the 'view' command for WordWise CLI that displays all saved words
from the SQLite database in a tabular format.
"""
import os
import sqlite3
from datetime import datetime

from .base import Command
from wordwise.registry import register_command
from ..data.database import get_connection


@register_command
class ViewCommand(Command):
    """Command to view all saved words."""

    @property
    def name(self):
        """Return the command name."""
        return "view"

    @property
    def description(self):
        """Return the command description."""
        return "Display all saved words from the database"

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        # Add optional --status flag with valid choices
        parser.add_argument(
            "--status",
            choices=["to-review", "learned"],
            help="Filter words by learning status ('to-review' or 'learned')"
        )

    def execute(self, args):
        """Execute the view command."""
        conn = get_connection()
        cursor = conn.cursor()

        # Build the query based on the status filter
        query = 'SELECT word, note, status, date_added FROM words'
        params = []

        if args.status:
            query += ' WHERE status = ?'
            params.append(args.status)

        query += ' ORDER BY date_added DESC'

        # Query words from the database with potential filtering
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Close connection
        conn.close()

        if not rows:
            # Customize message based on whether filtering was applied
            if args.status:
                print(f"No words with status '{args.status}' found.")
            else:
                print("No saved words found.")
            return

        # Print header with status information if filtering was applied
        if args.status:
            print(f"\n=== Saved Words (Status: {args.status}) ===\n")
        else:
            print("\n=== Saved Words ===\n")

        # Determine maximum width for each column
        max_word_len = max(len(row[0]) for row in rows)
        max_word_len = max(max_word_len, len("Word"))  # Ensure column header fits

        max_note_len = max(len(str(row[1] or "")) for row in rows)
        max_note_len = max(max_note_len, len("Note"))  # Ensure column header fits

        max_status_len = max(len(row[2]) for row in rows)
        max_status_len = max(max_status_len, len("Status"))  # Ensure column header fits

        # Format string for tabular output
        format_str = f"{{:<{max_word_len}}}  {{:<{max_note_len}}}  {{:<{max_status_len}}}  {{:<10}}"

        # Print table header
        print(format_str.format("Word", "Note", "Status", "Date Added"))
        print("-" * (max_word_len + max_note_len + max_status_len + 16))  # Divider line

        # Print table rows
        for word, note, status, date_added in rows:
            # Format date for display (keeping only the date part)
            try:
                display_date = datetime.fromisoformat(date_added).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                display_date = date_added  # Fallback to original string if parsing fails

            # Display note or empty string if None
            note_display = note if note else ""

            print(format_str.format(word, note_display, status, display_date))

        # Print summary with filtering information if applicable
        if args.status:
            print(f"\nTotal words with status '{args.status}': {len(rows)}")
        else:
            print(f"\nTotal words: {len(rows)}")