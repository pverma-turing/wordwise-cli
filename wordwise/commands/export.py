"""
Implementation of the 'export' command for WordWise CLI that exports saved words
to a CSV file.
"""
import os
import sqlite3
import sys
import csv
from datetime import datetime
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

    def execute(self, args):
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

        try:
            # Connect to the database
            conn = get_connection()
            cursor = conn.cursor()

            # Build and execute query with optional status filtering
            query = "SELECT word, note, status, date_added FROM words"

            # Apply filtering directly at SQL query level for efficiency
            if args.status != "all":
                query += " WHERE status = ?"
                cursor.execute(query, (args.status,))
            else:
                cursor.execute(query)

            # Fetch all results
            rows = cursor.fetchall()

            # If no rows found, inform user and exit
            if not rows:
                status_msg = f" with status '{args.status}'" if args.status != "all" else ""
                print(f"No words{status_msg} found to export.")
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

            # Provide success message that indicates when filtering was applied
            status_msg = f" with status '{args.status}'" if args.status != "all" else ""
            print(f"Successfully exported {row_count} words{status_msg} to {args.file}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except PermissionError:
            print(f"Error: Permission denied when writing to {args.file}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()