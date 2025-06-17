import sqlite3
import datetime
from .base import Command
from wordwise.data.database import get_connection
from wordwise.registry import register_command
from wordwise.utils.db_helpers import get_goal_value

@register_command
class ProgressCommand(Command):
    @property
    def name(self):
        return "progress"

    @property
    def description(self):
        return "Show today's word learning progress against your daily goal"

    def add_arguments(self, parser):
        # No additional arguments needed
        pass

    def execute(self, args):
        conn = None
        try:
            # Connect to database
            conn = get_connection()
            cursor = conn.cursor()

            # Get today's date in ISO format (YYYY-MM-DD)
            today = datetime.date.today().isoformat()

            # Count words saved today
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE date(date_added) = date(?)",
                (today,)
            )
            words_today = cursor.fetchone()[0]

            # Get the daily goal
            daily_goal = get_goal_value(conn, "daily_word_goal")

            # Generate appropriate message based on progress
            if words_today == 0:
                progress_msg = "You haven't saved any words today."
                if daily_goal is not None:
                    progress_msg += f" Your daily goal is {daily_goal}."
            else:
                progress_msg = f"You have saved {words_today} word{'s' if words_today != 1 else ''} today."

                if daily_goal is None:
                    progress_msg += " No daily goal set. Use set-goal to configure one."
                elif words_today >= daily_goal:
                    progress_msg = f"Goal met! {progress_msg}"
                else:
                    progress_msg += f" Your daily goal is {daily_goal}. Keep going!"

            print(progress_msg)

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()