# wordwise/commands/lookup.py
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
        return "Look up one or more words in the dictionary"

    def add_arguments(self, parser):
        parser.add_argument(
            "words",
            help="One or more words to look up",
            nargs="+",  # Accept one or more positional arguments
        )
        parser.add_argument(
            "--example", "-e",
            help="Include example usages in the output",
            action="store_true",
            default=False
        )
        parser.add_argument(
            "--synonyms", "-s",
            help="Include synonyms in the output",
            action="store_true",
            default=False
        )

    def execute(self, args):
        show_examples = args.example
        show_synonyms = args.synonyms
        success = False  # Track if at least one word was found

        # Process each word in the arguments
        for i, input_word in enumerate(args.words):
            # Add separator between multiple words
            if i > 0:
                print("\n" + "-" * 40)

            word = input_word.lower()

            # Case 1: Exact match
            if word in DICTIONARY:
                entry = DICTIONARY[word]
                print(format_dictionary_entry(
                    word, entry,
                    show_examples=show_examples,
                    show_synonyms=show_synonyms
                ))
                success = True
                continue

            # Try case-insensitive match
            found = False
            for dict_word in DICTIONARY:
                if dict_word.lower() == word:
                    entry = DICTIONARY[dict_word]
                    print(format_dictionary_entry(
                        dict_word, entry,
                        show_examples=show_examples,
                        show_synonyms=show_synonyms
                    ))
                    success = True
                    found = True
                    break

            if found:
                continue

            # Case 2: No exact match, try to find similar words
            similar_words = find_similar_words(word, DICTIONARY.keys())

            if similar_words:
                first_suggestion = similar_words[0]
                print(f"Word '{input_word}' not found. Did you mean '{first_suggestion}'?")

                # Show the suggested word
                entry = DICTIONARY[first_suggestion]
                print(format_dictionary_entry(
                    first_suggestion, entry,
                    show_examples=show_examples,
                    show_synonyms=show_synonyms
                ))

                # Show additional suggestions
                if len(similar_words) > 1:
                    other_suggestions = similar_words[1:][:3]  # Up to 3 more suggestions
                    if other_suggestions:
                        print("\nOther similar words:")
                        for suggestion in other_suggestions:
                            print(f"- {suggestion}")

                success = True
            else:
                # Case 3: No matches at all
                print(f"Word '{input_word}' not found. No similar words found.")

        # Return success if at least one word was processed successfully
        return 0 if success else 1