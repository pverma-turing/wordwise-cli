"""
Implementation of the 'export' command for WordWise CLI that exports saved words
to a CSV file.
"""
import json
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
    PRESET_DIR = Path.home() / ".wordwise" / "presets"
    PRESET_FILE = PRESET_DIR / "export_presets.json"
    @property
    def name(self):
        """Return the command name."""
        return "export"

    @property
    def description(self):
        """Return the command description."""
        return "Export saved words to a CSV file"

    def add_arguments(self, parser):
        # Create subparsers for export commands
        subparsers = parser.add_subparsers(dest="export_command", help="Export command to run")

        # Create the default export parser (standard export functionality)
        export_parser = subparsers.add_parser("export", help="Export words to a file")
        self._add_export_arguments(export_parser)

        # Create the save-preset parser
        save_preset_parser = subparsers.add_parser("save-preset", help="Save current export settings as a preset")
        self._add_export_arguments(save_preset_parser)  # Same args as export
        save_preset_parser.add_argument(
            "preset_name",
            help="Name of the preset to save"
        )

        # Create the run-preset parser
        run_preset_parser = subparsers.add_parser("run-preset", help="Run a previously saved export preset")
        run_preset_parser.add_argument(
            "preset_name",
            help="Name of the preset to run"
        )
        run_preset_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be exported without writing any file"
        )

        # Create the list-presets parser
        list_presets_parser = subparsers.add_parser("list-presets", help="List all available export presets")
        list_presets_parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed preset configurations"
        )

        # Add arguments to the default parser as well (for backward compatibility)
        self._add_export_arguments(parser)

    def _add_export_arguments(self, parser):
        """Add all export-related arguments to the given parser."""
        # Existing file argument
        parser.add_argument(
            "--file",
            required=False,
            help="Path to the file where words will be exported"
        )

        # Format selection argument
        parser.add_argument(
            "--format",
            choices=["csv", "markdown", "flashcard"],
            default="csv",
            help="Output format (csv, markdown, or flashcard)"
        )

        # Field selection argument
        parser.add_argument(
            "--fields",
            type=str,
            help="Comma-separated list of fields to export (word,note,status,date_added)"
        )

        # Encoding argument
        parser.add_argument(
            "--encoding",
            type=str,
            default="utf-8",
            help="File encoding (e.g., utf-8, utf-16, ascii); defaults to utf-8"
        )

        # Dry-run argument
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be exported without writing any file"
        )

        # Append argument
        parser.add_argument(
            "--append",
            action="store_true",
            help="Append to existing file instead of overwriting it"
        )

        # Status filter argument
        parser.add_argument(
            "--status",
            choices=["all", "learned", "to-review"],
            default="all",
            help="Filter words by learning status (all, learned, or to-review)"
        )

        # Date range filter arguments
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

        # Text search argument
        parser.add_argument(
            "--search",
            type=str,
            help="Export only words containing this text (case-insensitive)"
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

    def _write_csv_format(self, file_path, rows, fields, encoding='utf-8', append=False):
        """Write data in CSV format with only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}
        file_exists = os.path.exists(file_path)
        mode = 'a' if append and file_exists else 'w'
        with open(file_path, mode, newline='', encoding=encoding) as file:
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

    def _write_markdown_format(self, file_path, rows, fields, encoding="utf-8", append=False):
        """Write data in Markdown table format with only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}
        file_exists = os.path.exists(file_path)
        mode = 'a' if append and file_exists else 'w'
        with open(file_path, mode, encoding=encoding) as file:
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

    def _write_flashcard_format(self, file_path, rows, fields, encoding="utf-8", append=False):
        """Write data in flashcard format using only the selected fields."""
        field_indices = {field: i for i, field in enumerate(["word", "note", "status", "date_added"])}
        field_headers = {"word": "Word", "note": "Note", "status": "Status", "date_added": "Date Added"}
        file_exists = os.path.exists(file_path)
        mode = 'a' if append and file_exists else 'w'
        with open(file_path, mode, encoding=encoding) as file:
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

    def _load_presets(self):
        """Load export presets from the JSON file."""
        # Ensure the preset directory exists
        self.PRESET_DIR.mkdir(parents=True, exist_ok=True)

        if not self.PRESET_FILE.exists():
            return {}

        try:
            with open(self.PRESET_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Preset file is corrupted. Starting with empty presets.")
            return {}
        except Exception as e:
            print(f"Error loading presets: {e}")
            return {}

    def _save_presets(self, presets):
        """Save export presets to the JSON file."""
        # Ensure the preset directory exists
        self.PRESET_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.PRESET_FILE, 'w') as f:
                json.dump(presets, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving presets: {e}")
            return False

    def _get_preset_config(self, args):
        """Extract export configuration from args for saving as a preset."""
        # Include all export-related settings
        config = {
            "file": args.file,
            "format": args.format,
            "encoding": args.encoding,
            "append": args.append,
            "status": args.status,
        }

        # Include optional arguments only if specified
        if args.fields:
            config["fields"] = args.fields
        if args.from_date:
            config["from_date"] = args.from_date
        if args.to_date:
            config["to_date"] = args.to_date
        if args.search:
            config["search"] = args.search

        return config

    def _create_args_from_preset(self, preset_config, override_args=None):
        """Create an args namespace from a preset configuration.

        If override_args is provided, those values will override the preset values.
        """
        from argparse import Namespace

        # Create args from preset
        args = Namespace()
        for key, value in preset_config.items():
            setattr(args, key, value)

        # Apply any overrides
        if override_args:
            for key, value in vars(override_args).items():
                # Only override if the value is not None (explicitly set)
                if hasattr(override_args, key) and value is not None:
                    setattr(args, key, value)

        return args

    def _save_preset(self, args):
        """Save the current export settings as a preset."""
        preset_name = args.preset_name

        # Load existing presets
        presets = self._load_presets()

        # Extract export config from args
        preset_config = self._get_preset_config(args)

        # Check if preset already exists
        if preset_name in presets:
            confirmation = input(f"Preset '{preset_name}' already exists. Overwrite? (y/n): ")
            if confirmation.lower() not in ["y", "yes"]:
                print("Save preset cancelled.")
                return False

        # Save the preset
        presets[preset_name] = preset_config
        if self._save_presets(presets):
            print(f"Preset '{preset_name}' saved successfully.")
            return True
        else:
            print(f"Failed to save preset '{preset_name}'.")
            return False

    def _run_preset(self, args):
        """Run a previously saved export preset."""
        preset_name = args.preset_name

        # Load existing presets
        presets = self._load_presets()

        # Check if preset exists
        if preset_name not in presets:
            print(f"Error: Preset '{preset_name}' not found.")
            # Show available presets to help the user
            self._list_presets(args, show_header=True)
            return False

        # Get preset configuration
        preset_config = presets[preset_name]

        # Create args from preset config, overriding with any explicit arguments
        preset_args = self._create_args_from_preset(preset_config, args)

        # Set export_command to ensure it's processed as a standard export
        preset_args.export_command = None

        # Run the export with the preset args
        return self._run_export(preset_args)

    def _list_presets(self, args, show_header=False):
        """List all available export presets."""
        # Load existing presets
        presets = self._load_presets()

        # Check if there are any presets
        if not presets:
            print("No export presets found.")
            return True

        # Show presets
        if show_header:
            print("\nAvailable export presets:")
        else:
            print("\nExport presets:")

        # Sort preset names for consistent display
        preset_names = sorted(presets.keys())

        if not hasattr(args, 'verbose') or not args.verbose:
            # Simple list view
            for name in preset_names:
                preset = presets[name]
                format_type = preset.get('format', 'csv').upper()
                file_path = preset.get('file', 'N/A')
                print(f"  {name}: {format_type} -> {file_path}")
        else:
            # Verbose view with all settings
            for name in preset_names:
                preset = presets[name]
                print(f"\n  {name}:")

                # Display each setting with proper formatting
                print(f"    File: {preset.get('file', 'N/A')}")
                print(f"    Format: {preset.get('format', 'csv').upper()}")

                if 'fields' in preset:
                    print(f"    Fields: {preset['fields']}")
                else:
                    print(f"    Fields: All fields")

                print(f"    Encoding: {preset.get('encoding', 'utf-8')}")
                print(f"    Append mode: {'Yes' if preset.get('append', False) else 'No'}")

                # Show filters
                filters = []
                if preset.get('status', 'all') != 'all':
                    filters.append(f"status='{preset['status']}'")
                if preset.get('from_date'):
                    filters.append(f"from={preset['from_date']}")
                if preset.get('to_date'):
                    filters.append(f"to={preset['to_date']}")
                if preset.get('search'):
                    filters.append(f"search='{preset['search']}'")

                if filters:
                    print(f"    Filters: {', '.join(filters)}")
                else:
                    print(f"    Filters: None")

        return True

    def _run_export(self, args):
        # Check if the target directory exists (skip in dry-run mode)
        file_path = Path(args.file)
        directory = file_path.parent

        if not args.dry_run and not os.path.exists(directory):
            print(f"Error: Directory {directory} does not exist.")
            return

    def execute(self, args):
        # Check if a subcommand was specified
        if hasattr(args, 'export_command') and args.export_command:
            if args.export_command == "export":
                # Standard export with explicit subcommand
                return self._run_export(args)
            elif args.export_command == "save-preset":
                # Save current settings as a preset
                return self._save_preset(args)
            elif args.export_command == "run-preset":
                # Run a saved preset
                return self._run_preset(args)
            elif args.export_command == "list-presets":
                # List all available presets
                return self._list_presets(args)

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

        if not args.dry_run and not os.path.exists(directory):
            print(f"Error: Directory {directory} does not exist.")
            return

        # Check if file exists and confirm overwrite (skip in dry-run mode)
        file_exists = os.path.exists(file_path)

        if not args.dry_run and file_exists:
            if args.append:
                # In append mode, no confirmation needed
                pass
            else:
                # In overwrite mode, confirm before proceeding
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

            row_count = len(rows)
            if args.dry_run:
                print(f"DRY RUN: Would export {row_count} words{filter_msg}")
                print(f"Format:   {args.format.upper()}")

                if fields_msg:
                    print(f"Fields:   {', '.join(selected_fields)}")
                else:
                    print(f"Fields:   All fields (word, note, status, date_added)")

                print(f"Encoding: {args.encoding}")
                print(f"File:     {args.file}")
                print("No files were written (dry run mode)")
                return

            else:
                # Write data in the selected format, using only the selected fields
                if args.format == "csv":
                    row_count = self._write_csv_format(file_path, rows, selected_fields, args.encoding, args.append)
                elif args.format == "markdown":
                    row_count = self._write_markdown_format(file_path, rows, selected_fields, args.encoding, args.append)
                elif args.format == "flashcard":
                    row_count = self._write_flashcard_format(file_path, rows, selected_fields, args.encoding, args.append)

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