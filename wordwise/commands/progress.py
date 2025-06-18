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
        # Add optional history argument
        parser.add_argument(
            "--history",
            type=int,
            help="Show progress history for the past N days",
            metavar="N"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate and display progress without updating the streaks database"
        )

    def _get_history_data(self, conn, days):
        """Get progress history data for the specified number of days.

        Args:
            conn (sqlite3.Connection): Database connection
            days (int): Number of days of history to retrieve

        Returns:
            list: List of dictionaries containing history data, one per day
        """
        cursor = conn.cursor()
        today = datetime.date.today()
        history_data = []

        # Process each day
        for i in range(days):
            # Calculate the date for this history entry
            date = today - datetime.timedelta(days=i)
            date_str = date.isoformat()

            # Get words saved on this date
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE date(date_added) = date(?)",
                (date_str,)
            )
            words_saved = cursor.fetchone()[0]

            # Get goal value for this date (assume same goal for all days)
            daily_goal = get_goal_value(conn, "daily_word_goal")

            # Get whether goal was met
            cursor.execute(
                "SELECT goal_met FROM streaks WHERE date = ?",
                (date_str,)
            )
            goal_met_record = cursor.fetchone()
            goal_met = goal_met_record[0] if goal_met_record else 'N/A'

            # Calculate streak as of this date
            previous_date = (date - datetime.timedelta(days=1)).isoformat()
            streak_result = calculate_current_streak(conn, previous_date)
            streak_count, _ = streak_result

            # If goal was met on this day, add one to the streak
            if goal_met_record and goal_met_record[0]:
                streak_count += 1
            elif goal_met_record and not goal_met_record[0]:
                streak_count = 0

            # Add entry to history data
            history_data.append({
                'date': date_str,
                'words_saved': words_saved,
                'goal': daily_goal if daily_goal is not None else 'N/A',
                'goal_met': 'Yes' if goal_met_record and goal_met_record[0] else
                ('No' if goal_met_record else 'N/A'),
                'streak': streak_count
            })

        return history_data

    def _print_history_table(self, history_data):
        """Print history data in a tabular format.

        Args:
            history_data (list): List of dictionaries containing history data
        """
        if not history_data:
            print("No history data available.")
            return

        # Print table header
        print("\nProgress History:")
        print("-" * 70)
        print(f"{'Date':<12} | {'Words Saved':<11} | {'Goal':<6} | {'Goal Met':<8} | {'Streak':<6}")
        print("-" * 70)

        # Print table rows
        for entry in history_data:
            print(f"{entry['date']:<12} | {entry['words_saved']:<11} | {entry['goal']:<6} | "
                  f"{entry['goal_met']:<8} | {entry['streak']:<6}")

        print("-" * 70)

    def execute(self, args):
        conn = None
        try:
            # Connect to database
            conn = get_connection()
            cursor = conn.cursor()

            # If history flag is provided, show history data
            if args.history and args.history > 0:
                # Get and display history data
                history_data = self._get_history_data(conn, args.history)
                self._print_history_table(history_data)
                return

            # Otherwise, show regular progress view
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

            # Determine if goal was met and record streak (unless dry run)
            goal_met = False
            if daily_goal is not None:
                goal_met = words_today >= daily_goal
                if not args.dry_run:
                    record_streak(conn, today, goal_met)
                elif args.dry_run and goal_met:
                    print("(Dry run: Would record goal as met)")
                elif args.dry_run and not goal_met:
                    print("(Dry run: Would record goal as not met)")

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
                elif daily_goal - words_today == 1:
                    # Special encouraging message when user is just 1 word away from their goal
                    progress_msg += f" Almost there! Just 1 more word to reach your goal!"
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