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
        # Add time argument that accepts either "morning" or "evening"
        parser.add_argument(
            "--time",
            choices=["morning", "evening"],
            help="Specify time of day for customized reminders"
        )

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

            # Query 3: Get the user's daily word goal if set
            daily_goal = self._get_daily_word_goal(cursor)

            # Determine user activity status for today
            has_activity_today = words_added_today > 0 or reviews_today > 0

            # Generate and display the appropriate message
            if has_activity_today:
                self._show_positive_message(words_added_today, reviews_today, args.time, daily_goal)
            else:
                self._show_reminder_message(args.time, daily_goal)

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()

    def _get_daily_word_goal(self, cursor):
        """Retrieve the user's daily word goal from settings table."""
        try:
            # Check if settings table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
            )
            if cursor.fetchone():
                # If it exists, check for the daily_word_goal setting
                cursor.execute(
                    "SELECT value FROM settings WHERE key = 'daily_word_goal'"
                )
                result = cursor.fetchone()
                if result:
                    try:
                        return int(result[0])
                    except (ValueError, TypeError):
                        return None
            return None
        except sqlite3.Error:
            return None

    def _format_goal_progress(self, words_added_today, daily_goal):
        """Format the goal progress message if a goal is set."""
        if daily_goal is None:
            return ""

        percentage = min(100, int((words_added_today / daily_goal) * 100))

        if words_added_today >= daily_goal:
            return f"\n🎯 Daily goal achieved! {words_added_today} of {daily_goal} words saved today ({percentage}%)."
        else:
            return f"\n🎯 Daily goal: {words_added_today} of {daily_goal} words saved today ({percentage}%)."

    def _show_positive_message(self, words_added, reviews_done, time_of_day=None, daily_goal=None):
        """Display a positive reinforcement message, optionally customized for time of day."""
        if time_of_day == "morning":
            positive_messages = [
                "Great start to your day with some language practice!",
                "Morning practice sets a positive tone for the day!",
                "Starting your day with learning shows great dedication!",
                "Morning review sessions are a fantastic habit!",
                "Your morning language practice is setting you up for success today."
            ]
        elif time_of_day == "evening":
            positive_messages = [
                "Excellent job fitting in language practice before the day ends!",
                "Winding down your day with some learning - perfect!",
                "Evening practice sessions are great for memory consolidation!",
                "Great way to conclude your day with some language learning!",
                "Your evening dedication to learning is impressive!"
            ]
        else:
            # Default positive messages (no time specified)
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

        # Add goal progress if a goal is set
        if daily_goal:
            print(self._format_goal_progress(words_added, daily_goal))

        # Add a suggestion for continued practice based on time of day
        if time_of_day == "morning":
            print("\nConsider scheduling another review session later today to reinforce your learning!\n")
        elif time_of_day == "evening":
            print(
                "\nGreat job completing your practice today. Plan tomorrow's learning session for continued progress!\n")
        else:
            print("\nConsider doing more reviews or adding new words to enhance your learning!\n")

    def _show_reminder_message(self, time_of_day=None, daily_goal=None):
        """Display a motivational reminder message, optionally customized for time of day."""
        if time_of_day == "morning":
            reminder_messages = [
                "Start your day with a quick review!",
                "Morning is the perfect time to learn something new!",
                "Kickstart your brain with some language practice this morning.",
                "Begin your day with 5 minutes of vocabulary practice.",
                "Morning vocabulary practice sets a positive tone for the day ahead."
            ]
        elif time_of_day == "evening":
            reminder_messages = [
                "Wind down your day by practicing your words.",
                "Before the day ends, take a moment for language learning.",
                "Evening is a great time to reinforce your vocabulary skills.",
                "End your day on a productive note with a quick word review.",
                "Round off your day with a few minutes of language practice."
            ]
        else:
            # Default reminder messages (no time specified)
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

        # Add goal progress if a goal is set
        if daily_goal:
            print(self._format_goal_progress(0, daily_goal))

        # Add contextual suggestions based on time of day
        if time_of_day == "morning":
            print("\nStarting with a review session improves retention throughout the day.")
            print("Use 'wordwise review' to get your day off to a productive start.\n")
        elif time_of_day == "evening":
            print("\nEvening review helps consolidate what you've learned during the day.")
            print("Try 'wordwise review' for a relaxing but productive end to your day.\n")
        else:
            print("\nUse 'wordwise review' to practice your saved words.")
            print("Or try 'wordwise lookup <word>' to explore and save new words.\n")