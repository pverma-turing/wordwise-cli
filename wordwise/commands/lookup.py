# wordwise/commands/lookup.py
"""Lookup command for WordWise."""

import argparse
import json

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
        parser.add_argument(
            "--format", "-f",
            help="Output format (text or json)",
            choices=["text", "json"],
            default="text"
        )
        parser.add_argument(
            "--offline", "-o",
            help="Force using only the offline dictionary source",
            action="store_true",
            default=False
        )

    def execute(self, args):
        show_examples = args.example
        show_synonyms = args.synonyms
        format_type = args.format
        offline_mode = args.offline
        success = False  # Track if at least one word was found

        # Notify user if offline mode is active
        if offline_mode and format_type == "text":
            print("Using offline dictionary source")

        # For JSON output, collect all results in a list
        json_results = []

        # Process each word in the arguments
        for i, input_word in enumerate(args.words):
            # Add separator between multiple words in text format
            if format_type == "text" and i > 0:
                print("\n" + "-" * 40)

            word = input_word.lower()
            result = {}  # For storing JSON result

            # Case 1: Exact match
            if word in DICTIONARY:
                entry = DICTIONARY[word]
                if format_type == "text":
                    print(format_dictionary_entry(
                        word, entry,
                        show_examples=show_examples,
                        show_synonyms=show_synonyms
                    ))
                else:  # JSON format
                    result = self._prepare_json_result(
                        word, entry,
                        show_examples=show_examples,
                        show_synonyms=show_synonyms,
                        status="found",
                        offline=offline_mode
                    )
                success = True

            else:
                # Try case-insensitive match
                found = False
                for dict_word in DICTIONARY:
                    if dict_word.lower() == word:
                        entry = DICTIONARY[dict_word]
                        if format_type == "text":
                            print(format_dictionary_entry(
                                dict_word, entry,
                                show_examples=show_examples,
                                show_synonyms=show_synonyms
                            ))
                        else:  # JSON format
                            result = self._prepare_json_result(
                                dict_word, entry,
                                show_examples=show_examples,
                                show_synonyms=show_synonyms,
                                status="found",
                                offline=offline_mode
                            )
                        success = True
                        found = True
                        break

                if not found:
                    # Case 2: No exact match, try to find similar words
                    similar_words = find_similar_words(word, DICTIONARY.keys())

                    if similar_words:
                        first_suggestion = similar_words[0]
                        if format_type == "text":
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
                                other_suggestions = similar_words[1:][:3]
                                if other_suggestions:
                                    print("\nOther similar words:")
                                    for suggestion in other_suggestions:
                                        print(f"- {suggestion}")
                        else:  # JSON format
                            entry = DICTIONARY[first_suggestion]
                            result = self._prepare_json_result(
                                first_suggestion, entry,
                                show_examples=show_examples,
                                show_synonyms=show_synonyms,
                                status="suggestion",
                                original_query=input_word,
                                other_suggestions=similar_words[1:][:3] if len(similar_words) > 1 else [],
                                offline=offline_mode
                            )

                        success = True
                    else:
                        # Case 3: No matches at all
                        if format_type == "text":
                            print(f"Word '{input_word}' not found. No similar words found.")
                        else:  # JSON format
                            result = {
                                "query": input_word,
                                "status": "not_found",
                                "message": "No similar words found",
                                "source": "offline" if offline_mode else "auto"
                            }

            # Add result to JSON output collection if using JSON format
            if format_type == "json" and result:
                json_results.append(result)

        # Output JSON at the end if JSON format was requested
        if format_type == "json":
            # If only one word was looked up, return a single object instead of a list
            if len(json_results) == 1:
                print(json.dumps(json_results[0], indent=2))
            else:
                print(json.dumps(json_results, indent=2))

        # Return success if at least one word was processed successfully
        return 0 if success else 1

    def _prepare_json_result(self, word, entry, show_examples=False, show_synonyms=False,
                             status="found", original_query=None, other_suggestions=None,
                             offline=False):
        """
        Prepare a JSON result for a word lookup.

        Args:
            word: The word found or suggested
            entry: Dictionary entry for the word
            show_examples: Whether to include examples
            show_synonyms: Whether to include synonyms
            status: Lookup status ("found" or "suggestion")
            original_query: Original query if this is a suggestion
            other_suggestions: List of other suggestions
            offline: Whether offline mode is active

        Returns:
            Dictionary formatted for JSON output
        """
        result = {
            "word": word,
            "status": status,
            "source": "offline" if offline else "auto"
        }

        if original_query:
            result["original_query"] = original_query

        # Always include definition
        if "definition" in entry:
            result["definition"] = entry["definition"]

        # Include synonyms if requested
        if show_synonyms and "synonyms" in entry and entry["synonyms"]:
            result["synonyms"] = entry["synonyms"]

        # Include examples if requested
        if show_examples and "examples" in entry and entry["examples"]:
            result["examples"] = entry["examples"]

        # Include other suggestions if available
        if other_suggestions:
            result["other_suggestions"] = other_suggestions

        return result