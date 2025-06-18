import sqlite3
from .base import Command
from wordwise.data.database import get_connection
from wordwise.registry import register_command


@register_command
class SetGoalCommand(Command):
    @property
    def name(self):
        return "set-goal"

    @property
    def description(self):
        return "Set a daily word learning goal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            required=True,
            help="Number of words to learn daily (0 to remove goal)"
        )

    def execute(self, args):
        if args.count < 0:
            print("Error: Goal count must be a non-negative integer")
            return

        conn = None
        try:
            # Connect to database
            conn = get_connection()
            cursor = conn.cursor()

            # Create settings table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            ''')

            # Check if a goal already exists
            cursor.execute("SELECT value FROM settings WHERE key = 'daily_word_goal'")
            existing_goal = cursor.fetchone()

            if args.count == 0:
                # Remove the goal if count is 0
                if existing_goal:
                    cursor.execute("DELETE FROM settings WHERE key = 'daily_word_goal'")
                    print("Daily word goal has been removed.")
                else:
                    print("No daily word goal was set.")
            else:
                # Set or update the goal
                if existing_goal:
                    cursor.execute(
                        "UPDATE settings SET value = ? WHERE key = 'daily_word_goal'",
                        (str(args.count),)
                    )
                    print(f"Daily word goal updated to {args.count} words.")
                else:
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES ('daily_word_goal', ?)",
                        (str(args.count),)
                    )
                    print(f"Daily word goal set to {args.count} words.")

            conn.commit()

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()