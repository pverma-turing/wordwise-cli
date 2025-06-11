"""
Implementation of the 'export' command for WordWise CLI that exports saved words
to a CSV file.
"""
import os
import sys
import csv
from datetime import datetime

from .base import Command
from wordwise.data.database import get_connection
from wordwise.registry import register_command


@register_command
class ExportCommand(Command):
    """Command to export saved words to a CSV file."""

    @property
    def name(self):
        """Return the command name."""
        return "export"

    @property
    def description(self):
        """Return the command description."""
        return "Export saved words to a CSV file"

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the export CSV file"
        )

    def execute(self, args):
        """Execute the export command."""
        # Create database directory if it doesn't exist

        # Validate file path is not empty
        if not args.file or args.file.strip() == "":
            print("Error: Export file path cannot be empty.")
            return

        # Check if the directory is writable before proceeding
        file_dir = os.path.dirname(args.file) or '.'
        if not os.access(file_dir, os.W_OK):
            print(f"Cannot write to file '{args.file}'. Check directory permissions and try again.")
            sys.exit(1)

        conn = get_connection()
        cursor = conn.cursor()

        # Query all words from the database
        cursor.execute('SELECT word, note, status, date_added FROM words ORDER BY word ASC')
        rows = cursor.fetchall()

        # Close database connection
        conn.close()

        if not rows:
            print("No saved words to export.")
            return

        # Export words to CSV file
        try:
            with open(args.file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write header row
                writer.writerow(['Word', 'Note', 'Status', 'Date Added'])

                # Write data rows
                for word, note, status, date_added in rows:
                    # Format date for display (keeping only the date part)
                    try:
                        display_date = datetime.fromisoformat(date_added).strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        display_date = date_added  # Fallback to original string if parsing fails

                    # Handle None values in notes
                    note_display = note if note else ""

                    writer.writerow([word, note_display, status, display_date])

                print(f"Successfully exported {len(rows)} words to {args.file}")

        except IOError as e:
            print(f"Error exporting to file '{args.file}': {e}")
            sys.exit(1)