# wordwise/commands/save.py
"""Save command implementation."""

import argparse
from wordwise.commands.base import Command
from wordwise.registry import register_command
from wordwise.data.database import save_word
from wordwise.data.dictionary import DICTIONARY


@register_command
class SaveCommand(Command):
    """Command to save words for future review."""

    @property
    def name(self):
        return "save"

    @property
    def description(self):
        return "Save a word to your personal collection"

    def add_arguments(self, parser):
        parser.add_argument("word", help="The word to save")
        parser.add_argument(
            "--note", "-n",
            help="Optional note about the word",
            default=None
        )

    def execute(self, args):
        word = args.word.lower()

        # Inform user if word isn't in our dictionary
        if word not in DICTIONARY:
            print(f"Note: '{word}' is not in the built-in dictionary.")

        # Try to save the word
        if save_word(word, args.note):
            print(f"✅ Successfully saved '{word}' to your collection.")
            if args.note:
                print(f"Note: {args.note}")
            return 0
        else:
            print(f"❌ '{word}' is already in your collection.")
            return 1