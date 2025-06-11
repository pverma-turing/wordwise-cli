import datetime
import random
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
    with options to filter by due date, limit the number of words, resume
    incomplete review sessions, and shuffle the review order.
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
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Resume an incomplete review by skipping already reviewed words"
        )
        parser.add_argument(
            "--shuffle",
            action="store_true",
            help="Randomize the order of words for review"
        )

    def _has_column(self, cursor, table_name, column_name):
        """Check if the given column exists in the specified table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        return column_name in columns

    def _ensure_last_review_result_column(self, cursor):
        """Ensure the last_review_result column exists in the words table."""
        if not self._has_column(cursor, "words", "last_review_result"):
            try:
                cursor.execute("ALTER TABLE words ADD COLUMN last_review_result TEXT")
                return True
            except sqlite3.Error as e:
                print(f"Warning: Could not add last_review_result column: {e}")
                return False
        return True

    def _get_valid_recall_input(self):
        """Get a valid recall assessment input (y/n) from the user."""
        while True:
            response = input("Did you recall the word correctly? (y/n): ").strip().lower()
            if response in ['y', 'n']:
                return response == 'y'  # Return True for 'y', False for 'n'
            print("Please enter 'y' for correct or 'n' for incorrect.")

    def _update_review_result(self, cursor, word, recall_correct):
        """Update the last_review_result for the given word."""
        result = "correct" if recall_correct else "incorrect"
        try:
            cursor.execute(
                "UPDATE words SET last_review_result = ? WHERE word = ?",
                (result, word)
            )
            return True
        except sqlite3.Error as e:
            print(f"Warning: Could not update review result for '{word}': {e}")
            return False

    def execute(self, args):
        """Execute the review command with the provided arguments."""
        # Connect to the database
        conn = None
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row  # Use Row factory to access columns by name
            cursor = conn.cursor()

            # Ensure the last_review_result column exists
            column_added = self._ensure_last_review_result_column(cursor)
            if column_added:
                conn.commit()

            # Build the query based on the arguments
            query_parts = ["SELECT word, note, date_added, status, rowid FROM words"]
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

            # Add resume condition if specified
            if args.resume and self._has_column(cursor, "words", "last_review_result"):
                conditions.append("(last_review_result IS NULL)")

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
            words = list(cursor.fetchall())  # Convert to list to support shuffling

            # Check if there are any words to review
            if not words:
                if args.resume:
                    print("No new words to review. All available words have already been reviewed.")
                elif args.due_only:
                    print("No words are due for review.")
                else:
                    print("You have no saved words to review.")
                return

            # Shuffle the words if requested
            if args.shuffle:
                random.shuffle(words)
                shuffle_message = "Words have been randomized for this review session."
            else:
                shuffle_message = ""

            # Display the number of words to review
            print(f"You have {len(words)} word(s) to review.")
            if args.resume:
                print("Resuming from where you left off (skipping previously reviewed words).")
            if shuffle_message:
                print(shuffle_message)
            print("Press Enter after each word to continue to the next one.")
            print("-" * 40)

            # Track correct recalls for summary
            total_words = len(words)
            correct_recalls = 0

            # Display each word and wait for user input
            for i, word_row in enumerate(words, 1):
                word = word_row['word']
                note = word_row['note']
                date_added = word_row['date_added']
                status = word_row['status']

                print(f"\nWord {i}/{total_words}:")
                print(f"{word}")

                # Get self-assessment from user
                recall_correct = self._get_valid_recall_input()

                # Update the last_review_result in the database
                update_success = self._update_review_result(cursor, word, recall_correct)
                if update_success:
                    conn.commit()

                if recall_correct:
                    correct_recalls += 1
                    print("Great job!")
                else:
                    print("Don't worry, you'll get it next time!")

                input("Press Enter to see details...")

                # Display information about the word
                print(f"\nStatus: {status}")
                print(f"Added on: {date_added}")

                if note:
                    print("\nYour note:")
                    print(f"{note}")

                if i < total_words:
                    input("\nPress Enter for the next word...")
                    print("\n" + "-" * 40)

            # Display summary after review is complete
            print("\nReview complete. You recalled",
                  f"{correct_recalls} out of {total_words} words correctly.")
            print("Your results have been saved to the database.")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            sys.exit(1)
        finally:
            if conn:
                conn.close()