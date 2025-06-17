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

        parser.add_argument(
            "--fields",
            type=str,
            help="Comma-separated list of fields to export (word,note,status,date_added)"
        )

        parser.add_argument(
            "--encoding",
            type=str,
            default="utf-8",
            help="File encoding (e.g., utf-8, utf-16, ascii); defaults to utf-8"
        )

    def _validate_date(self, date_str):
        """Validate that a date string is in YYYY-MM-DD format."""
        try:
            dt.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _parse_fields(self, fields_arg):
        """Parse and validate the fields argument, returning a list of valid field names."""
        valid_fields = ["word", "note", "status", "date_added"]
        default_fields = valid_fields.copy()

        if not fields_arg:
            return default_fields

        selected_fields = [field.strip().lower() for field in fields_arg.split(',')]

        # Validate fields
        invalid_fields = [field for field in selected_fields if field not in valid_fields]
        if invalid_fields:
            raise ValueError(f"Invalid field(s): {', '.join(invalid_fields)}. "
                             f"Valid fields are: {', '.join(valid_fields)}")

        # Ensure at least one valid field
        valid_selected = [field for field in selected_fields if field in valid_fields]
        if not valid_selected:
            raise ValueError(f"No valid fields selected. Valid fields are: {', '.join(valid_fields)}")

        return valid_selected

    def _write_csv_format(self, file_path, rows, fields, encoding='utf-8'):
        """Write data in CSV format with only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}

        with open(file_path, 'w', newline='', encoding=encoding) as file:
            writer = csv.writer(file)
            # Write selected field headers
            headers = [field_headers[field] for field in fields]
            writer.writerow(headers)

            for row in rows:
                # Extract only the selected fields from each row
                values = []
                for field in fields:
                    idx = field_indices[field]
                    value = row[idx]
                    # Handle null values
                    if field == "note" and value is None:
                        value = ""
                    values.append(value)
                writer.writerow(values)

        return len(rows)

    def _write_markdown_format(self, file_path, rows, fields, encoding="utf-8"):
        """Write data in Markdown table format with only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}

        with open(file_path, 'w', encoding=encoding) as file:
            # Write markdown table header with selected fields
            header_row = "| " + " | ".join([field_headers[field] for field in fields]) + " |"
            file.write(header_row + "\n")

            # Write the separator line with correct number of columns
            separator = "|" + "|".join(["---" for _ in fields]) + "|"
            file.write(separator + "\n")

            # Write data rows with only the selected fields
            for row in rows:
                values = []
                for field in fields:
                    idx = field_indices[field]
                    value = row[idx]
                    # Handle null values
                    if field == "note" and value is None:
                        value = ""
                    # Escape pipe characters for markdown
                    if value is not None:
                        value = str(value).replace("|", "\\|")
                    values.append(value)
                file.write("| " + " | ".join(values) + " |\n")

        return len(rows)

    def _write_flashcard_format(self, file_path, rows, fields, encoding="utf-8"):
        """Write data in flashcard format using only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}

        with open(file_path, 'w', encoding=encoding) as file:
            for row in rows:
                # Build flashcard format based on available fields
                parts = []

                # Always start with word if it's selected (or default to first selected field)
                if "word" in fields:
                    parts.append(row[field_indices["word"]])
                elif fields:  # If word is not selected, use the first selected field
                    first_field = fields[0]
                    parts.append(f"{field_headers[first_field]}: {row[field_indices[first_field]]}")

                # Add remaining fields with labels
                remaining_fields = [f for f in fields if f != "word" and
                                    (f != fields[0] or "word" in fields)]

                for field in remaining_fields:
                    idx = field_indices[field]
                    value = row[idx]
                    if field == "note" and value is None:
                        value = ""
                    if field == "status":
                        parts.append(f"[{value}]")
                    else:
                        parts.append(f"{field}: {value}")

                file.write(" - ".join(parts) + "\n")

        return len(rows)

    def _validate_encoding(self, encoding):
        """Validate that the specified encoding is supported by Python."""
        try:
            "test".encode(encoding).decode(encoding)
            return True
        except (LookupError, UnicodeEncodeError, UnicodeDecodeError):
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

        if not self._validate_encoding(args.encoding):
            print(f"Error: '{args.encoding}' is not a valid encoding.")
            return

        if args.encoding != "utf-8":  # Only mention encoding if not default
            print(f" using {args.encoding} encoding")

        # Parse and validate fields
        try:
            selected_fields = self._parse_fields(args.fields)
        except ValueError as e:
            print(f"Error: {e}")
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
                print("Export cancelled. Please try again")
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

            # Always fetch all fields from the database for consistency
            # Field selection will be applied at the output stage
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

            # Write data in the selected format, using only the selected fields
            if args.format == "csv":
                row_count = self._write_csv_format(file_path, rows, selected_fields, args.encoding)
            elif args.format == "markdown":
                row_count = self._write_markdown_format(file_path, rows, selected_fields, args.encoding)
            elif args.format == "flashcard":
                row_count = self._write_flashcard_format(file_path, rows, selected_fields, args.encoding)

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

            # Include format and fields info in success message
            fields_msg = ""
            if len(selected_fields) < 4:  # Only mention fields if not all fields are selected
                fields_msg = f" with fields: {', '.join(selected_fields)}"

            print(
                f"Successfully exported {row_count} words{filter_msg} to {args.file} in {args.format.upper()} format{fields_msg}")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except PermissionError:
            print(f"Error: Permission denied when writing to {args.file}")
        except ValueError as e:
            print(f"Error with field selection: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()