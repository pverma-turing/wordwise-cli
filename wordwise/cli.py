# wordwise/cli.py
# !/usr/bin/env python3
"""
CLI entry point for the WordWise application.
"""

import argparse
import sys

from wordwise.commands import RemindCommand
from wordwise.config import COMMANDS
from wordwise.version import __version__


def create_parser():
    """Create the main argument parser with subcommands."""
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="WordWise - A Smart Command-Line Dictionary & Word Learning App",
        prog="wordwise"
    )

    # Add version argument to the main parser
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"WordWise CLI version {__version__}",
        help="Show program's version number and exit"
    )

    # Create subparsers for each command
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Command to execute"
    )

    # Make subparsers required only if --version is not present
    # This is handled manually below since we can't conditionally set required

    # Register all commands from the registry
    for command_name, command_class in COMMANDS.items():
        command_instance = command_class()
        command_parser = subparsers.add_parser(
            command_name,
            help=command_instance.description
        )
        command_instance.add_arguments(command_parser)

    return parser


def main():
    """Main entry point for the CLI."""
    # Parse command line arguments
    parser = create_parser()

    # Parse known arguments first to check if --version is present
    args, remaining = parser.parse_known_args()

    # If --version is present, it will be handled automatically by argparse
    # and the program will exit after printing the version

    # If we reach this point, --version was not present or has been handled
    # Re-parse with full argument validation
    args = parser.parse_args()

    # If no command was provided and --version wasn't used, show help
    if not hasattr(args, 'command') or args.command is None:
        parser.print_help()
        reminder_message = RemindCommand.get_latest_reminder()
        if reminder_message:
            # Display the startup header
            print("\n===== WordWise Daily Reminder =====")
            # Remove the leading newline since we're adding our own
            if reminder_message.startswith('\n'):
                reminder_message = reminder_message[1:]
            print(reminder_message)
            print("=================================\n")
        return 1

    # Get the command class and instantiate it
    command_class = COMMANDS.get(args.command)
    if not command_class:
        print(f"Unknown command: {args.command}")
        return 1

    # Execute the command
    command_instance = command_class()
    return command_instance.execute(args)


if __name__ == "__main__":
    sys.exit(main())