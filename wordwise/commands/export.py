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

    def _validate_date(self, date_str):
        """Validate that a date string is in YYYY-MM-DD format."""
        try:
            dt.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

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

        if not directory.exists():
            print(f"Error: Directory {directory} does not exist.")
            return

        # Check if file exists and confirm overwrite
        if file_path.exists():
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

            # Add each filter condition if specified
            if args.status != "all":
                conditions.append("status = ?")
                params.append(args.status)

            if args.from_date:
                conditions.append("date_added >= ?")
                params.append(args.from_date)

            if args.to_date:
                conditions.append("date_added <= ?")
                params.append(args.to_date)

            # Build complete query with all conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Execute the query with parameters
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

                filter_msg = ""
                if filter_parts:
                    filter_msg = f" with {' and '.join(filter_parts)}"

                print(f"No words found{filter_msg} to export.")
                return

            # Write data to CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csv_file:
                csv_writer = csv.writer(csv_file)

                # Write header row
                csv_writer.writerow(['Word', 'Note', 'Status', 'Date Added'])

                # Write data rows
                row_count = 0
                for row in rows:
                    word, note, status, date_added = row
                    # Handle None values for note
                    note = note if note is not None else ""

                    csv_writer.writerow([word, note, status, date_added])
                    row_count += 1

            # Build detailed filter message for success output
            filter_parts = []
            if args.status != "all":
                filter_parts.append(f"status '{args.status}'")
            if args.from_date:
                filter_parts.append(f"from {args.from_date}")
            if args.to_date:
                filter_parts.append(f"to {args.to_date}")

            filter_msg = ""
            if filter_parts:
                filter_msg = f" (filtered by: {', '.join(filter_parts)})"

            print(f"Successfully exported {row_count} words{filter_msg} to {args.file}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except PermissionError:
            print(f"Error: Permission denied when writing to {args.file}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()