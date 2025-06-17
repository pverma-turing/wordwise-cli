"""
Implementation of the 'export' command for WordWise CLI that exports saved words
to a CSV file.
"""
import os
import sqlite3
import sys
import csv
from datetime import datetime as dt
from pathlib import Path

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
        parser.add_argument(
            "--status",
            choices=["all", "learned", "to-review"],
            default="all",
            help="Filter words by learning status (all, learned, or to-review)"
        )
        # New date range filter arguments
        parser.add_argument(
            "--from-date",
            type=str,
            help="Export words added on or after this date (YYYY-MM-DD)"
        )

        parser.add_argument(
            "--to-date",
            type=str,
            help="Export words added on or before this date (YYYY-MM-DD)"
        )

        # New text search argument
        parser.add_argument(
            "--search",
            type=str,
            help="Export only words containing this text (case-insensitive)"
        )

        parser.add_argument(
            "--format",
            choices=["csv", "markdown", "flashcard"],
            default="csv",
            help="Output format (csv, markdown, or flashcard)"
        )

    def _validate_date(self, date_str):
        """Validate that a date string is in YYYY-MM-DD format."""
        try:
            dt.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _write_csv_format(self, file_path, rows):
        """Write data in CSV format."""
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Word', 'Note', 'Status', 'Date Added'])
            for row in rows:
                word, note, status, date_added = row
                note = note if note is not None else ""
                writer.writerow([word, note, status, date_added])
        return len(rows)

    def _write_markdown_format(self, file_path, rows):
        """Write data in Markdown table format."""
        with open(file_path, 'w', encoding='utf-8') as file:
            # Write markdown table header
            file.write("| Word | Note | Status | Date Added |\n")
            file.write("|------|------|--------|------------|\n")
            # Write data rows
            for row in rows:
                word, note, status, date_added = row
                note = note if note is not None else ""
                # Escape pipe characters in values for markdown table
                word = word.replace("|", "\\|")
                note = note.replace("|", "\\|")
                status = status.replace("|", "\\|")
                file.write(f"| {word} | {note} | {status} | {date_added} |\n")
        return len(rows)

    def _write_flashcard_format(self, file_path, rows):
        """Write data in simple flashcard text format."""
        with open(file_path, 'w', encoding='utf-8') as file:
            for row in rows:
                word, note, status, date_added = row
                note = note if note is not None else ""
                file.write(f"{word}: {note} [{status}]\n")
        return len(rows)

    def execute(self, args):
        # Validate date formats if provided
        if args.from_date and not self._validate_date(args.from_date):
            print(f"Error: Invalid date format for --from-date. Use YYYY-MM-DD.")
            return

        if args.to_date and not self._validate_date(args.to_date):
            print(f"Error: Invalid date format for --to-date. Use YYYY-MM-DD.")
            return

        # Add date logical validation: from_date should be before to_date
        if args.from_date and args.to_date and args.from_date > args.to_date:
            print(f"Error: --from-date ({args.from_date}) must be on or before --to-date ({args.to_date}).")
            return

        # Check if the target directory exists
        file_path = Path(args.file)
        directory = file_path.parent

        if not os.path.exists(directory):
            print(f"Error: Directory {directory} does not exist.")
            return

        # Check if file exists and confirm overwrite
        if os.path.exists(file_path):
            confirmation = input(f"File {args.file} already exists. Overwrite? (y/n): ")
            if confirmation.lower() not in ["y", "yes"]:
                print("Export cancelled.")
                return

        conn = None
        try:
            # Connect to the database
            conn = get_connection()
            cursor = conn.cursor()

            # Check if words table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words'")
            if not cursor.fetchone():
                print("No saved words database found.")
                return

            # Build query with multiple potential conditions
            query = "SELECT word, note, status, date_added FROM words"
            conditions = []
            params = []

            # Apply all filters
            if args.status != "all":
                conditions.append("status = ?")
                params.append(args.status)

            if args.from_date:
                conditions.append("date_added >= ?")
                params.append(args.from_date)

            if args.to_date:
                conditions.append("date_added <= ?")
                params.append(args.to_date)

            if args.search:
                conditions.append("LOWER(word) LIKE LOWER(?)")
                params.append(f"%{args.search}%")

            # Add WHERE clause if any conditions exist
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Execute query with parameters
            cursor.execute(query, params)

            # Fetch all results
            rows = cursor.fetchall()

            # If no rows found, inform user and exit
            if not rows:
                # Build a message about applied filters
                filter_parts = []
                if args.status != "all":
                    filter_parts.append(f"status '{args.status}'")
                if args.from_date:
                    filter_parts.append(f"from {args.from_date}")
                if args.to_date:
                    filter_parts.append(f"to {args.to_date}")
                if args.search:
                    filter_parts.append(f"containing '{args.search}'")

                filter_msg = ""
                if filter_parts:
                    filter_msg = f" with {' and '.join(filter_parts)}"

                print(f"No words found{filter_msg} to export.")
                return

            # Write data in the selected format
            if args.format == "csv":
                row_count = self._write_csv_format(file_path, rows)
            elif args.format == "markdown":
                row_count = self._write_markdown_format(file_path, rows)
            elif args.format == "flashcard":
                row_count = self._write_flashcard_format(file_path, rows)

            # Build detailed filter message for success output
            filter_parts = []
            if args.status != "all":
                filter_parts.append(f"status '{args.status}'")
            if args.from_date:
                filter_parts.append(f"from {args.from_date}")
            if args.to_date:
                filter_parts.append(f"to {args.to_date}")
            if args.search:
                filter_parts.append(f"containing '{args.search}'")

            filter_msg = ""
            if filter_parts:
                filter_msg = f" (filtered by: {', '.join(filter_parts)})"

            # Include format in success message
            print(f"Successfully exported {row_count} words{filter_msg} to {args.file} in {args.format.upper()} format")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except PermissionError:
            print(f"Error: Permission denied when writing to {args.file}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()