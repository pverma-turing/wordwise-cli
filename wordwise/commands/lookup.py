"""Lookup command for WordWise."""

import argparse
from wordwise.commands.base import Command
from wordwise.registry import register_command
from wordwise.data.dictionary import DICTIONARY
from wordwise.utils.formatter import format_dictionary_entry


@register_command
class LookupCommand(Command):
    """Command to look up words in the dictionary."""

    @property
    def name(self):
        return "lookup"

    @property
    def description(self):
        return "Look up a word in the dictionary"

    def add_arguments(self, parser):
        parser.add_argument(
            "word",
            help="The word to look up"
        )

    def execute(self, args):
        word = args.word.lower()

        if word in DICTIONARY:
            entry = DICTIONARY[word]
            print(format_dictionary_entry(word, entry))
            return 0
        else:
            print(f"Word '{word}' not found in the dictionary.")
            return 1