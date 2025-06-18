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
        # Add custom message argument
        parser.add_argument(
            "--custom-message",
            type=str,
            help="Provide a custom message to display instead of the default motivational message"
        )
        # Add argument for configuring startup reminders
        parser.add_argument(
            "--startup",
            choices=["enable", "disable"],
            help="Configure whether to show reminders automatically on CLI startup"
        )

    def execute(self, args):
        # Get the DB path - using the same approach as other commands
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Handle startup configuration if provided
            if hasattr(args, 'startup') and args.startup:
                self._configure_startup_reminder(cursor, args.startup == "enable")
                conn.commit()
                state = "enabled" if args.startup == "enable" else "disabled"
                print(f"Automatic startup reminders {state}.")
                return

            # Ensure the reminder_history table exists
            self._ensure_reminder_history_table(cursor)
            # Ensure the settings table exists
            self._ensure_settings_table(cursor)

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

            # Generate and display the appropriate message, and log it
            if has_activity_today:
                message = self._show_positive_message(
                    words_added_today, reviews_today, args.time, daily_goal, args.custom_message
                )
                self._log_reminder(cursor, "positive", message)
            else:
                message = self._show_reminder_message(
                    args.time, daily_goal, args.custom_message
                )
                self._log_reminder(cursor, "reminder", message)

            # Commit the transaction to save the reminder log
            conn.commit()

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_latest_reminder():
        """
        Retrieves the latest reminder from the database.
        This method is intended to be called from the CLI entry point.

        Returns:
            str: The latest reminder message, or None if no reminders exist or if startup reminders are disabled
        """
        # Get the DB path
        db_dir = os.path.join(os.path.expanduser("~"), ".wordwise")
        db_path = os.path.join(db_dir, "words.db")

        # If the database doesn't exist yet, return None
        if not os.path.exists(db_path):
            return None

        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if startup reminders are enabled
            cursor.execute(
                "SELECT value FROM settings WHERE key = 'show_reminder_on_startup'"
            )
            result = cursor.fetchone()
            if not result or result[0].lower() != 'true':
                return None

            # Check if the reminder_history table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reminder_history'"
            )
            if not cursor.fetchone():
                return None

            # Get the latest reminder
            cursor.execute(
                "SELECT message_text FROM reminder_history ORDER BY timestamp DESC LIMIT 1"
            )
            result = cursor.fetchone()

            if result:
                return result[0]
            return None

        except sqlite3.Error:
            return None
        finally:
            if conn:
                conn.close()

    def _configure_startup_reminder(self, cursor, enable):
        """Configure whether to show reminders on startup."""
        self._ensure_settings_table(cursor)

        # Set the show_reminder_on_startup setting
        value = 'true' if enable else 'false'
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ('show_reminder_on_startup', value)
        )

    def _ensure_settings_table(self, cursor):
        """Create the settings table if it doesn't exist."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

    def _ensure_reminder_history_table(self, cursor):
        """Create the reminder_history table if it doesn't exist."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                message_text TEXT NOT NULL
            )
        ''')

    def _log_reminder(self, cursor, reminder_type, message_text):
        """Log the reminder to the reminder_history table."""
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO reminder_history (timestamp, type, message_text) VALUES (?, ?, ?)",
            (timestamp, reminder_type, message_text)
        )

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

    def _show_positive_message(self, words_added, reviews_done, time_of_day=None, daily_goal=None, custom_message=None):
        """Display a positive reinforcement message, optionally customized."""
        # Determine the main message (custom or default)
        if custom_message:
            main_message = f"✨ {custom_message}"
        else:
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
            main_message = f"🎉 {message}"

        # Print the main message
        print(f"\n{main_message}")

        # Build the full message for logging
        full_message = main_message

        # Add activity details
        activity_message = ""
        if words_added > 0 and reviews_done > 0:
            activity_message = f"Today you've added {words_added} new word(s) and completed {reviews_done} review(s)."
        elif words_added > 0:
            activity_message = f"Today you've added {words_added} new word(s) to your collection."
        elif reviews_done > 0:
            activity_message = f"Today you've reviewed {reviews_done} word(s) in your collection."

        if activity_message:
            print(activity_message)
            full_message += f"\n{activity_message}"

        # Add goal progress if a goal is set
        if daily_goal:
            goal_message = self._format_goal_progress(words_added, daily_goal)
            print(goal_message)
            full_message += goal_message

        # Add a suggestion based on time of day
        suggestion_message = ""
        if time_of_day == "morning":
            suggestion_message = "\nConsider scheduling another review session later today to reinforce your learning!"
        elif time_of_day == "evening":
            suggestion_message = "\nGreat job completing your practice today. Plan tomorrow's learning session for continued progress!"
        else:
            suggestion_message = "\nConsider doing more reviews or adding new words to enhance your learning!"

        print(f"{suggestion_message}\n")
        full_message += f"{suggestion_message}"

        return full_message

    def _show_reminder_message(self, time_of_day=None, daily_goal=None, custom_message=None):
        """Display a motivational reminder message, optionally customized."""
        # Determine the main message (custom or default)
        if custom_message:
            main_message = f"✨ {custom_message}"
        else:
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
            main_message = f"⏰ {message}"

        # Print the main message
        print(f"\n{main_message}")

        # Build the full message for logging
        full_message = main_message

        # Add goal progress if a goal is set
        if daily_goal:
            goal_message = self._format_goal_progress(0, daily_goal)
            print(goal_message)
            full_message += goal_message

        # Add contextual suggestions based on time of day
        suggestion_message = ""
        if time_of_day == "morning":
            suggestion_message = "\nStarting with a review session improves retention throughout the day."
            suggestion_message += "\nUse 'wordwise review' to get your day off to a productive start."
        elif time_of_day == "evening":
            suggestion_message = "\nEvening review helps consolidate what you've learned during the day."
            suggestion_message += "\nTry 'wordwise review' for a relaxing but productive end to your day."
        else:
            suggestion_message = "\nUse 'wordwise review' to practice your saved words."
            suggestion_message += "\nOr try 'wordwise lookup <word>' to explore and save new words."

        print(f"{suggestion_message}\n")
        full_message += f"{suggestion_message}"

        return full_message