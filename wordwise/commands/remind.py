import datetime
import sqlite3
from .base import Command
import os
import random

from wordwise.registry import register_command
from wordwise.data.database import get_connection


@register_command
class RemindCommand(Command):
    @property
    def name(self):
        return "remind"

    @property
    def description(self):
        return "Check daily learning activity and provide motivational reminders"

    def add_arguments(self, parser):
        # No additional arguments needed for this command
        pass

    def execute(self, args):
        # Get the DB path - using the same approach as other commands
        db_dir = os.path.join(os.path.expanduser("~"), ".wordwise")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "words.db")

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get today's date in ISO format for comparison
            today = datetime.datetime.now().date().isoformat()

            # Query 1: Check if any words were added today
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE date_added LIKE ?",
                (f"{today}%",)
            )
            words_added_today = cursor.fetchone()[0]

            # Query 2: Check if any words were reviewed today
            has_review_table = False
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='review_sessions'"
            )
            if cursor.fetchone():
                has_review_table = True
                cursor.execute(
                    "SELECT COUNT(*) FROM review_sessions WHERE session_date LIKE ?",
                    (f"{today}%",)
                )
                reviews_today = cursor.fetchone()[0]
            else:
                # If review_sessions table doesn't exist yet, check last_review_date in words table
                cursor.execute(
                    "SELECT COUNT(*) FROM pragma_table_info('words') WHERE name='last_review_date'"
                )
                has_review_date = cursor.fetchone()[0] > 0

                if has_review_date:
                    cursor.execute(
                        "SELECT COUNT(*) FROM words WHERE last_review_date LIKE ?",
                        (f"{today}%",)
                    )
                    reviews_today = cursor.fetchone()[0]
                else:
                    reviews_today = 0

            # Determine user activity status for today
            has_activity_today = words_added_today > 0 or reviews_today > 0

            # Generate and display the appropriate message
            if has_activity_today:
                self._show_positive_message(words_added_today, reviews_today)
            else:
                self._show_reminder_message()

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()

    def _show_positive_message(self, words_added, reviews_done):
        """Display a positive reinforcement message."""
        positive_messages = [
            "Great job! You've already practiced today.",
            "Excellent work on your language learning today!",
            "Keep up the good work! Your consistency is paying off.",
            "Your dedication to learning is impressive!",
            "You're on a roll! Your language skills are growing every day."
        ]

        # Choose a random positive message
        message = random.choice(positive_messages)
        print("\n🎉 " + message)

        # Add specific details about their activity
        if words_added > 0 and reviews_done > 0:
            print(f"Today you've added {words_added} new word(s) and completed {reviews_done} review(s).")
        elif words_added > 0:
            print(f"Today you've added {words_added} new word(s) to your collection.")
        elif reviews_done > 0:
            print(f"Today you've reviewed {reviews_done} word(s) in your collection.")

        # Add a suggestion for continued practice
        print("Consider doing more reviews or adding new words to enhance your learning!\n")

    def _show_reminder_message(self):
        """Display a motivational reminder message."""
        reminder_messages = [
            "You haven't practiced today — take 5 minutes now to review your words!",
            "A quick review session will help strengthen your memory. How about now?",
            "Learning a little each day adds up! Take a moment to practice today.",
            "Make progress on your language journey with just 5 minutes of practice today.",
            "Consistency is key to language learning! Don't break your streak today."
        ]

        # Choose a random reminder message
        message = random.choice(reminder_messages)
        print("\n⏰ " + message)
        print("Use 'wordwise review' to practice your saved words.")
        print("Or try 'wordwise lookup <word>' to explore and save new words.\n")