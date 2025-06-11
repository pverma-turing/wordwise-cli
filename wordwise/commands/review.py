import datetime
import sqlite3
import sys
from typing import List, Optional

from wordwise.commands.base import Command
from wordwise.data.database import get_connection
from wordwise.registry import register_command


@register_command
class ReviewCommand(Command):
    """Command for reviewing previously saved words.

    This command allows users to review words they have saved in the database,
    with options to filter by due date and limit the number of words.
    """

    @property
    def name(self) -> str:
        return "review"

    @property
    def description(self) -> str:
        return "Review saved words to reinforce learning"

    def add_arguments(self, parser):
        """Add review-specific arguments to the parser."""
        parser.add_argument(
            "--due-only",
            action="store_true",
            help="Show only words that are due for review (next review date <= today)"
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of words to review",
            default=None
        )

    def execute(self, args):
        """Execute the review command with the provided arguments."""
        # Connect to the database
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Build the query based on the arguments
            query = "SELECT word, note, date_added, status FROM words"
            params = []

            conditions = []
            if args.due_only:
                today = datetime.date.today().isoformat()
                # Check if next_review_date exists in the schema, if not use status
                try:
                    cursor.execute("PRAGMA table_info(words)")
                    columns = [info[1] for info in cursor.fetchall()]

                    if "next_review_date" in columns:
                        conditions.append("(next_review_date <= ? OR next_review_date IS NULL)")
                        params.append(today)
                    else:
                        # Fallback to status for compatibility
                        conditions.append("status = 'to-review'")
                except sqlite3.Error:
                    # If error, just use status as fallback
                    conditions.append("status = 'to-review'")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add limit if specified
            if args.limit is not None:
                if args.limit <= 0:
                    print("Error: Limit must be a positive integer.")
                    sys.exit(1)
                query += " LIMIT ?"
                params.append(args.limit)

            # Execute the query
            cursor.execute(query, params)
            words = cursor.fetchall()

            # Check if there are any words to review
            if not words:
                if args.due_only:
                    print("No words are due for review.")
                else:
                    print("You have no saved words to review.")
                return

            # Display the number of words to review
            print(f"You have {len(words)} word(s) to review.")
            print("Press Enter after each word to continue to the next one.")
            print("-" * 40)

            # Display each word and wait for user input
            for i, (word, note, date_added, status) in enumerate(words, 1):
                print(f"\nWord {i}/{len(words)}:")
                print(f"{word}")
                input("Press Enter to see details...")

                # Display information about the word
                print(f"\nStatus: {status}")
                print(f"Added on: {date_added}")

                if note:
                    print("\nYour note:")
                    print(f"{note}")

                if i < len(words):
                    input("\nPress Enter for the next word...")
                    print("\n" + "-" * 40)

            print("\nReview completed!")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return
        finally:
            if conn:
                conn.close()