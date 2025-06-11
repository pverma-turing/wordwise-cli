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

    def _has_column(self, cursor, table_name, column_name):
        """Check if the given column exists in the specified table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        return column_name in columns

    def execute(self, args):
        """Execute the review command with the provided arguments."""
        # Connect to the database
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Build the query based on the arguments
            query_parts = ["SELECT word, note, date_added, status FROM words"]
            conditions = []
            params = []

            # Check if the next_review_date column exists
            has_next_review_date = self._has_column(cursor, "words", "next_review_date")

            if args.due_only:
                today = datetime.date.today().isoformat()

                if has_next_review_date:
                    # Filter by next_review_date when available
                    conditions.append("(next_review_date IS NOT NULL AND next_review_date <= ?)")
                    params.append(today)
                else:
                    # Fallback to status for backwards compatibility
                    conditions.append("status = 'to-review'")

            # Apply WHERE conditions if any exist
            if conditions:
                query_parts.append("WHERE " + " AND ".join(conditions))

            # Add limit if specified
            if args.limit is not None:
                if args.limit <= 0:
                    print("Error: Limit must be a positive integer.")
                    sys.exit(1)
                query_parts.append("LIMIT ?")
                params.append(args.limit)

            # Build and execute the final query
            query = " ".join(query_parts)
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
            sys.exit(1)
        finally:
            if conn:
                conn.close()