"""Lookup command for WordWise."""

import argparse
from wordwise.commands.base import Command
from wordwise.registry import register_command
from wordwise.data.dictionary import DICTIONARY
from wordwise.utils.formatter import format_dictionary_entry
from wordwise.utils.matching import find_similar_words


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

        # Case 1: Exact match
        if word in DICTIONARY:
            entry = DICTIONARY[word]
            print(format_dictionary_entry(word, entry))
            return 0

        # Try case-insensitive match first
        for dict_word in DICTIONARY:
            if dict_word.lower() == word:
                entry = DICTIONARY[dict_word]
                print(format_dictionary_entry(dict_word, entry))
                return 0

        # Case 2: No exact match, try to find similar words
        similar_words = find_similar_words(word, DICTIONARY.keys())

        if similar_words:
            first_suggestion = similar_words[0]
            print(f"Word '{args.word}' not found. Did you mean '{first_suggestion}'?")

            # If we have a suggestion, show it
            entry = DICTIONARY[first_suggestion]
            print(format_dictionary_entry(first_suggestion, entry))

            # If we have more suggestions, show them too
            if len(similar_words) > 1:
                other_suggestions = similar_words[1:][:3]  # Take up to 3 more suggestions
                if other_suggestions:
                    print("\nOther similar words:")
                    for suggestion in other_suggestions:
                        print(f"- {suggestion}")

            return 0

        # Case 3: No matches at all
        print(f"Word '{args.word}' not found. No similar words found.")
        return 1