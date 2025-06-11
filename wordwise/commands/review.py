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
    incomplete review sessions, shuffle the review order, reset review results,
    or just display a summary of available words.
    Users can also pause a review session at any time.
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
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset last_review_result to NULL for all selected words before review"
        )
        parser.add_argument(
            "--summary-only",
            action="store_true",
            help="Display a summary of words matching current filters without starting a review session"
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

    def _check_for_pause(self):
        """Check if user wants to pause the session."""
        response = input("Press Enter to continue, or type 'pause' to end the session here: ").strip().lower()
        return response == 'pause'

    def _build_query_conditions(self, args, has_next_review_date, has_last_review_result):
        """Build query conditions based on command arguments."""
        conditions = []
        params = []

        if args.due_only:
            today = datetime.date.today().isoformat()

            if has_next_review_date:
                # Filter by next_review_date when available
                conditions.append("(next_review_date IS NOT NULL AND next_review_date <= ?)")
                params.append(today)
            else:
                # Fallback to status for backwards compatibility
                conditions.append("status = 'to-review'")

        # Add resume condition if specified and not resetting
        if args.resume and not args.reset and has_last_review_result:
            conditions.append("(last_review_result IS NULL)")
        elif not args.resume and not args.reset and has_last_review_result:
            # By default, skip reviewed words unless explicitly asked to resume or reset
            conditions.append("(last_review_result IS NULL)")

        return conditions, params

    def _reset_review_results(self, conn, cursor, args, has_last_review_result):
        """Reset last_review_result to NULL for words matching the current filters."""
        if not args.reset or not has_last_review_result:
            return 0  # Nothing to reset

        # Build conditions for resetting (same as for selecting, but without resume filter)
        has_next_review_date = self._has_column(cursor, "words", "next_review_date")
        conditions, params = self._build_query_conditions(args, has_next_review_date, False)

        # Build and execute the reset query
        reset_query = "UPDATE words SET last_review_result = NULL"
        if conditions:
            reset_query += " WHERE " + " AND ".join(conditions)

        try:
            cursor.execute(reset_query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            print(f"Warning: Could not reset review results: {e}")
            return 0

    def _get_due_words_count(self, cursor, has_next_review_date):
        """Get the count of words that are due for review."""
        today = datetime.date.today().isoformat()

        if has_next_review_date:
            query = "SELECT COUNT(*) FROM words WHERE next_review_date <= ?"
            cursor.execute(query, (today,))
        else:
            # Fallback to status for backwards compatibility
            query = "SELECT COUNT(*) FROM words WHERE status = 'to-review'"
            cursor.execute(query)

        return cursor.fetchone()[0]

    def _log_session(self, words_reviewed, correct_recalls, was_paused):
        """Log the review session to a file."""
        log_file = "review_sessions.log"
        timestamp = datetime.datetime.now().isoformat()
        status = "PAUSED" if was_paused else "COMPLETED"

        log_entry = (
            f"{timestamp} | "
            f"Words reviewed: {words_reviewed} | "
            f"Correct recalls: {correct_recalls} | "
            f"Session status: {status}\n"
        )

        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
            return True
        except (IOError, OSError) as e:
            print(f"Warning: Could not write to session log: {e}")
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
            has_last_review_result = self._ensure_last_review_result_column(cursor)
            if has_last_review_result:
                conn.commit()

            # Reset review results if requested
            if args.reset and has_last_review_result:
                reset_count = self._reset_review_results(conn, cursor, args, has_last_review_result)
                print(f"Reset review results for {reset_count} word(s).")

            # Check if the next_review_date column exists
            has_next_review_date = self._has_column(cursor, "words", "next_review_date")

            # Build query conditions based on arguments
            conditions, params = self._build_query_conditions(
                args, has_next_review_date, has_last_review_result
            )

            # Build the query based on the arguments
            query_parts = ["SELECT word, note, date_added, status, rowid FROM words"]

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

            # Get total due words count (before limit is applied)
            due_words_count = 0
            if args.due_only:
                due_words_count = len(words)  # Already filtered to due words
            else:
                due_words_count = self._get_due_words_count(cursor, has_next_review_date)

            # Check if there are any words to review
            if not words:
                if args.resume:
                    print("No new words to review. All available words have already been reviewed.")
                elif args.due_only:
                    print("No words are due for review.")
                else:
                    print("You have no saved words to review.")
                return

            # If summary-only flag is set, just show the summary and exit
            if args.summary_only:
                print(f"Summary of review session:")
                print(f"- Total words matching current filters: {len(words)}")
                print(f"- Words due for review: {due_words_count}")

                filter_info = []
                if args.due_only:
                    filter_info.append("due words only")
                if args.resume:
                    filter_info.append("unreviewed words only")
                if args.limit is not None:
                    filter_info.append(f"limited to {args.limit} words")

                if filter_info:
                    print(f"- Active filters: {', '.join(filter_info)}")

                return

            # Shuffle the words if requested
            if args.shuffle:
                random.shuffle(words)
                shuffle_message = "Words have been randomized for this review session."
            else:
                shuffle_message = ""

            # Display the number of words to review
            print(f"You have {len(words)} word(s) to review.")
            print("You can pause the session anytime by typing 'pause'.")
            if args.resume and not args.reset:
                print("Resuming from where you left off (skipping previously reviewed words).")
            if shuffle_message:
                print(shuffle_message)
            print("Press Enter after each word to continue to the next one.")
            print("-" * 40)

            # Track correct recalls for summary
            total_words = len(words)
            correct_recalls = 0
            words_reviewed = 0  # Track how many words were reviewed before pausing
            was_paused = False  # Track if session was paused

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
                    words_reviewed += 1

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
                    # Give user option to continue or pause
                    pause_requested = self._check_for_pause()
                    if pause_requested:
                        was_paused = True
                        print("\nSession paused. Your progress has been saved.")
                        print(f"You have reviewed {words_reviewed} of {total_words} words.")
                        print(f"You recalled {correct_recalls} out of {words_reviewed} words correctly.")
                        print("To continue reviewing remaining words, run the command again with --resume flag.")

                        # Log the paused session
                        log_success = self._log_session(words_reviewed, correct_recalls, was_paused)
                        if log_success:
                            print("Session logged to review_sessions.log")

                        return
                    print("\n" + "-" * 40)

            # Display summary after review is complete
            print("\nReview complete! You recalled",
                  f"{correct_recalls} out of {total_words} words correctly.")
            print("Your results have been saved to the database.")

            # Log the completed session
            log_success = self._log_session(words_reviewed, correct_recalls, was_paused)
            if log_success:
                print("Session logged to review_sessions.log")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            sys.exit(1)
        finally:
            if conn:
                conn.close()