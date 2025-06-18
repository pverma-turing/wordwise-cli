import sqlite3
import datetime
from .base import Command
from wordwise.data.database import get_connection
from wordwise.registry import register_command
from wordwise.utils.db_helpers import get_goal_value, record_streak, calculate_current_streak


@register_command
class ProgressCommand(Command):
    @property
    def name(self):
        return "progress"

    @property
    def description(self):
        return "Show today's word learning progress and your current streak"

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

            # Determine if goal was met and record streak
            goal_met = False
            if daily_goal is not None:
                goal_met = words_today >= daily_goal
                record_streak(conn, today, goal_met)

            # Generate progress message
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

            # Display streak information if a goal is set
            if daily_goal is None:
                # Do not show streak information if no goal is set
                pass
            else:
                # Calculate current streak (excluding today if today's result is not yet recorded)
                yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                streak_result = calculate_current_streak(conn, yesterday)
                current_streak, streak_broken_reason = streak_result

                # Update streak if today's goal was met
                if goal_met:
                    current_streak += 1

                # Display streak information
                if current_streak == 0:
                    if streak_broken_reason == "missed_day":
                        print("Current streak: 0 (you missed a day)")
                    elif streak_broken_reason == "goal_not_met":
                        print("Current streak: 0 (goal wasn't met yesterday)")
                    else:
                        print("No streak yet. Keep going!")
                elif current_streak == 1:
                    print("Current streak: 1 day")
                else:
                    print(f"Current streak: {current_streak} days")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()