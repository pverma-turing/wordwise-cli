import sqlite3

from wordwise.data.database import get_connection
from wordwise.registry import register_command
from .base import Command
from wordwise.utils.db_helpers import get_goal_value


@register_command
class GetGoalCommand(Command):
    @property
    def name(self):
        return "get-goal"

    @property
    def description(self):
        return "Display the current daily word learning goal"

    def add_arguments(self, parser):
        # No arguments needed
        pass

    def execute(self, args):
        conn = None
        try:
            # Connect to database
            conn = get_connection()

            # Get the daily goal
            goal_value = get_goal_value(conn, "daily_word_goal")

            if goal_value is not None:
                print(f"Current daily word goal: {goal_value} words")
            else:
                print("No daily goal has been set.")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()
