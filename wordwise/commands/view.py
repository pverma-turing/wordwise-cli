"""
Implementation of the 'view' command for WordWise CLI that displays all saved words
from the SQLite database in a tabular format.
"""
import sys
from datetime import datetime

from .base import Command
from wordwise.registry import register_command
from wordwise.data.database import get_connection


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
        return "Display saved words from the database with optional filtering"

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        # Add optional --status flag with valid choices
        parser.add_argument(
            "--status",
            choices=["to-review", "learned"],
            help="Filter words by learning status ('to-review' or 'learned')"
        )

        # Add date range filters
        parser.add_argument(
            "--from-date",
            help="Show words added on or after this date (format: YYYY-MM-DD)"
        )

        parser.add_argument(
            "--to-date",
            help="Show words added on or before this date (format: YYYY-MM-DD)"
        )

    def validate_date_format(self, date_str, arg_name):
        """Validate that a date string is in YYYY-MM-DD format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            print(f"Error: Invalid date format for {arg_name}. Please use YYYY-MM-DD format.")
            return False

    def execute(self, args):
        """Execute the view command."""
        # Validate date formats if provided
        if args.from_date and not self.validate_date_format(args.from_date, "--from-date"):
            sys.exit(1)

        if args.to_date and not self.validate_date_format(args.to_date, "--to-date"):
            sys.exit(1)

        conn = get_connection()
        cursor = conn.cursor()

        # Build the query based on the filters
        query = 'SELECT word, note, status, date_added FROM words'
        conditions = []
        params = []

        # Add status filter if provided
        if args.status:
            conditions.append('status = ?')
            params.append(args.status)

        # Add from_date filter if provided
        if args.from_date:
            # Convert to full datetime for comparison
            from_datetime = f"{args.from_date}T00:00:00"
            conditions.append('date_added >= ?')
            params.append(from_datetime)

        # Add to_date filter if provided
        if args.to_date:
            # Convert to full datetime for comparison (end of day)
            to_datetime = f"{args.to_date}T23:59:59"
            conditions.append('date_added <= ?')
            params.append(to_datetime)

        # Add WHERE clause if any conditions exist
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        # Add ordering
        query += ' ORDER BY date_added DESC'

        # Execute the query with parameters
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Close connection
        conn.close()

        # Handle case where no matching words are found
        if not rows:
            filter_desc = []
            if args.status:
                filter_desc.append(f"status '{args.status}'")
            if args.from_date:
                filter_desc.append(f"added on or after {args.from_date}")
            if args.to_date:
                filter_desc.append(f"added on or before {args.to_date}")

            if filter_desc:
                print(f"No words found matching: {', '.join(filter_desc)}.")
            else:
                print("No saved words found.")
            return

        # Build header based on active filters
        header_parts = ["=== Saved Words"]
        if args.status:
            header_parts.append(f"Status: {args.status}")

        date_range = []
        if args.from_date:
            date_range.append(f"From: {args.from_date}")
        if args.to_date:
            date_range.append(f"To: {args.to_date}")

        if date_range:
            header_parts.append(', '.join(date_range))

        header = f"\n{' ('.join(header_parts)}"
        if len(header_parts) > 1:  # If we have filters, close the parenthesis
            header += ")"

        print(f"{header} ===\n")

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

        # Build total words message with active filters
        total_msg = f"\nTotal words"
        filter_desc = []

        if args.status:
            filter_desc.append(f"with status '{args.status}'")
        if args.from_date or args.to_date:
            date_clause = "added"
            if args.from_date:
                date_clause += f" on or after {args.from_date}"
            if args.from_date and args.to_date:
                date_clause += " and"
            if args.to_date:
                if not args.from_date:
                    date_clause += " on or before"
                date_clause += f" {args.to_date}"
            filter_desc.append(date_clause)

        if filter_desc:
            total_msg += f" {' '.join(filter_desc)}"

        print(f"{total_msg}: {len(rows)}")