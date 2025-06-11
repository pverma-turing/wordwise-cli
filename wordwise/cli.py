# wordwise/cli.py
# !/usr/bin/env python3
"""
CLI entry point for the WordWise application.
"""

import argparse
import sys
from wordwise.config import COMMANDS


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="WordWise - A Smart Command-Line Dictionary & Word Learning App",
        prog="wordwise"
    )

    # Create subparsers for each command
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Command to execute"
    )
    subparsers.required = True

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
    args = parser.parse_args()

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