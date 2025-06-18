import datetime
import sqlite3
from .base import Command
import os
import random

from wordwise.registry import register_command
from wordwise.data.database import get_connection


@register_command
class RemindCommand(Command):
    # Language dictionaries for translations
    TRANSLATIONS = {
        "en": {
            # Positive messages
            "positive_default": [
                "Great job! You've already practiced today.",
                "Excellent work on your language learning today!",
                "Keep up the good work! Your consistency is paying off.",
                "Your dedication to learning is impressive!",
                "You're on a roll! Your language skills are growing every day."
            ],
            "positive_morning": [
                "Great start to your day with some language practice!",
                "Morning practice sets a positive tone for the day!",
                "Starting your day with learning shows great dedication!",
                "Morning review sessions are a fantastic habit!",
                "Your morning language practice is setting you up for success today."
            ],
            "positive_evening": [
                "Excellent job fitting in language practice before the day ends!",
                "Winding down your day with some learning - perfect!",
                "Evening practice sessions are great for memory consolidation!",
                "Great way to conclude your day with some language learning!",
                "Your evening dedication to learning is impressive!"
            ],
            # Reminder messages
            "reminder_default": [
                "You haven't practiced today — take 5 minutes now to review your words!",
                "A quick review session will help strengthen your memory. How about now?",
                "Learning a little each day adds up! Take a moment to practice today.",
                "Make progress on your language journey with just 5 minutes of practice today.",
                "Consistency is key to language learning! Don't break your streak today."
            ],
            "reminder_morning": [
                "Start your day with a quick review!",
                "Morning is the perfect time to learn something new!",
                "Kickstart your brain with some language practice this morning.",
                "Begin your day with 5 minutes of vocabulary practice.",
                "Morning vocabulary practice sets a positive tone for the day ahead."
            ],
            "reminder_evening": [
                "Wind down your day by practicing your words.",
                "Before the day ends, take a moment for language learning.",
                "Evening is a great time to reinforce your vocabulary skills.",
                "End your day on a productive note with a quick word review.",
                "Round off your day with a few minutes of language practice."
            ],
            # Streak messages
            "streak_risk": [
                "Your {streak_length}-day learning streak is at risk! Take a moment to practice today.",
                "Don't break your {streak_length}-day streak! A quick review session will keep it going.",
                "Protect your {streak_length}-day learning streak with a quick practice session.",
                "Just 5 minutes of practice will maintain your {streak_length}-day streak.",
                "Keep your momentum going! Your {streak_length}-day streak needs attention today."
            ],
            # Activity messages
            "activity_added_reviewed": "Today you've added {words_added} new word(s) and completed {reviews_done} review(s).",
            "activity_added": "Today you've added {words_added} new word(s) to your collection.",
            "activity_reviewed": "Today you've reviewed {reviews_done} word(s) in your collection.",
            # Goal messages
            "goal_achieved": "\n🎯 Daily goal achieved! {words_added} of {daily_goal} words saved today ({percentage}%).",
            "goal_progress": "\n🎯 Daily goal: {words_added} of {daily_goal} words saved today ({percentage}%).",
            # Suggestion messages
            "suggestion_morning": "\nConsider scheduling another review session later today to reinforce your learning!",
            "suggestion_evening": "\nGreat job completing your practice today. Plan tomorrow's learning session for continued progress!",
            "suggestion_default": "\nConsider doing more reviews or adding new words to enhance your learning!",
            # Streak suggestions
            "streak_suggestion_morning": "\nIt only takes a few minutes to maintain your streak.\nUse 'wordwise review' to get your day off to a productive start and keep your streak alive.",
            "streak_suggestion_evening": "\nThere's still time to maintain your progress before the day ends!\nTry 'wordwise review' for a quick session to preserve your streak.",
            "streak_suggestion_default": "\nMaintaining consistency is key to effective learning.\nUse 'wordwise review' or 'wordwise lookup <word>' to keep your streak going.",
            # Reminder suggestions
            "reminder_suggestion_morning": "\nStarting with a review session improves retention throughout the day.\nUse 'wordwise review' to get your day off to a productive start.",
            "reminder_suggestion_evening": "\nEvening review helps consolidate what you've learned during the day.\nTry 'wordwise review' for a relaxing but productive end to your day.",
            "reminder_suggestion_default": "\nUse 'wordwise review' to practice your saved words.\nOr try 'wordwise lookup <word>' to explore and save new words.",
            # Other text
            "forced_reminder_suffix": "(Forced reminder)",
            "gentle_no_reminder": "No reminder needed - you're doing fine!",
            "startup_enabled": "Automatic startup reminders enabled.",
            "startup_disabled": "Automatic startup reminders disabled."
        },
        "de": {
            # Positive messages (German)
            "positive_default": [
                "Gute Arbeit! Du hast heute bereits geübt.",
                "Ausgezeichnete Arbeit beim Sprachenlernen heute!",
                "Weiter so! Deine Konsequenz zahlt sich aus.",
                "Dein Engagement für das Lernen ist beeindruckend!",
                "Du bist auf einem guten Weg! Deine Sprachkenntnisse wachsen täglich."
            ],
            "positive_morning": [
                "Ein guter Start in den Tag mit etwas Sprachpraxis!",
                "Morgenübungen stimmen dich positiv für den Tag!",
                "Der Beginn deines Tages mit Lernen zeigt große Hingabe!",
                "Morgendliche Übungssitzungen sind eine fantastische Gewohnheit!",
                "Deine morgendliche Sprachpraxis bereitet dich auf einen erfolgreichen Tag vor."
            ],
            "positive_evening": [
                "Hervorragend, dass du vor Tagesende noch Sprachübungen eingebaut hast!",
                "Den Tag mit etwas Lernen ausklingen lassen - perfekt!",
                "Abendliche Übungssitzungen sind großartig für die Gedächtniskonsolidierung!",
                "Ein toller Abschluss deines Tages mit etwas Sprachenlernen!",
                "Dein abendliches Engagement für das Lernen ist beeindruckend!"
            ],
            # Reminder messages (German)
            "reminder_default": [
                "Du hast heute noch nicht geübt — nimm dir jetzt 5 Minuten Zeit für deine Wörter!",
                "Eine schnelle Übungssession hilft deinem Gedächtnis. Wie wäre es jetzt?",
                "Jeden Tag ein bisschen lernen summiert sich! Nimm dir heute einen Moment Zeit zum Üben.",
                "Mach Fortschritte auf deiner Sprachlernreise mit nur 5 Minuten Übung heute.",
                "Konsequenz ist der Schlüssel zum Sprachenlernen! Brich deine Serie heute nicht ab."
            ],
            "reminder_morning": [
                "Beginne deinen Tag mit einer schnellen Wiederholung!",
                "Der Morgen ist die perfekte Zeit, um etwas Neues zu lernen!",
                "Starte dein Gehirn mit etwas Sprachpraxis heute Morgen.",
                "Beginne deinen Tag mit 5 Minuten Vokabelübung.",
                "Morgendliche Vokabelübungen stimmen dich positiv für den bevorstehenden Tag."
            ],
            "reminder_evening": [
                "Lass deinen Tag mit etwas Wortübung ausklingen.",
                "Bevor der Tag endet, nimm dir einen Moment für das Sprachenlernen.",
                "Der Abend ist eine großartige Zeit, um deine Vokabelkenntnisse zu festigen.",
                "Beende deinen Tag mit einer schnellen Wortwiederholung.",
                "Runde deinen Tag mit ein paar Minuten Sprachpraxis ab."
            ],
            # Streak messages (German)
            "streak_risk": [
                "Deine {streak_length}-tägige Lernserie ist in Gefahr! Nimm dir einen Moment zum Üben.",
                "Brich deine {streak_length}-tägige Serie nicht! Eine kurze Übungssitzung hält sie aufrecht.",
                "Schütze deine {streak_length}-tägige Lernserie mit einer schnellen Übungssitzung.",
                "Nur 5 Minuten Übung erhalten deine {streak_length}-tägige Serie.",
                "Halte den Schwung aufrecht! Deine {streak_length}-tägige Serie braucht heute Aufmerksamkeit."
            ],
            # Activity messages (German)
            "activity_added_reviewed": "Heute hast du {words_added} neue Wörter hinzugefügt und {reviews_done} Wiederholungen abgeschlossen.",
            "activity_added": "Heute hast du {words_added} neue Wörter zu deiner Sammlung hinzugefügt.",
            "activity_reviewed": "Heute hast du {reviews_done} Wörter in deiner Sammlung wiederholt.",
            # Goal messages (German)
            "goal_achieved": "\n🎯 Tagesziel erreicht! {words_added} von {daily_goal} Wörtern heute gespeichert ({percentage}%).",
            "goal_progress": "\n🎯 Tagesziel: {words_added} von {daily_goal} Wörtern heute gespeichert ({percentage}%).",
            # Suggestion messages (German)
            "suggestion_morning": "\nÜberlege dir, später heute eine weitere Übungssitzung einzuplanen, um dein Lernen zu verstärken!",
            "suggestion_evening": "\nTolle Arbeit beim Üben heute. Plane deine morgige Lernsitzung für kontinuierlichen Fortschritt!",
            "suggestion_default": "\nDenk darüber nach, weitere Wiederholungen zu machen oder neue Wörter hinzuzufügen, um dein Lernen zu verbessern!",
            # Streak suggestions (German)
            "streak_suggestion_morning": "\nEs dauert nur wenige Minuten, um deine Serie aufrechtzuerhalten.\nVerwende 'wordwise review', um deinen Tag produktiv zu beginnen und deine Serie am Leben zu erhalten.",
            "streak_suggestion_evening": "\nEs ist noch Zeit, deinen Fortschritt aufrechtzuerhalten, bevor der Tag endet!\nProbiere 'wordwise review' für eine schnelle Sitzung, um deine Serie zu erhalten.",
            "streak_suggestion_default": "\nKonsequenz ist der Schlüssel zum effektiven Lernen.\nVerwende 'wordwise review' oder 'wordwise lookup <word>', um deine Serie fortzusetzen.",
            # Reminder suggestions (German)
            "reminder_suggestion_morning": "\nEine Übungssitzung am Morgen verbessert die Merkfähigkeit den ganzen Tag über.\nVerwende 'wordwise review', um deinen Tag produktiv zu beginnen.",
            "reminder_suggestion_evening": "\nAbendliche Wiederholung hilft, das tagsüber Gelernte zu festigen.\nProbiere 'wordwise review' für einen entspannten, aber produktiven Tagesabschluss.",
            "reminder_suggestion_default": "\nVerwende 'wordwise review', um deine gespeicherten Wörter zu üben.\nOder probiere 'wordwise lookup <word>', um neue Wörter zu entdecken und zu speichern.",
            # Other text (German)
            "forced_reminder_suffix": "(Erzwungene Erinnerung)",
            "gentle_no_reminder": "Keine Erinnerung nötig - alles in Ordnung!",
            "startup_enabled": "Automatische Starterinnerungen aktiviert.",
            "startup_disabled": "Automatische Starterinnerungen deaktiviert."
        }
    }

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
        # Add argument for gentle nudge behavior
        parser.add_argument(
            "--gentle",
            action="store_true",
            help="Only show reminders when your streak is at risk (no reminder if already practiced or low streak)"
        )
        # Add argument to force reminder display
        parser.add_argument(
            "--force",
            action="store_true",
            help="Always show a reminder regardless of practice status or gentle mode setting"
        )
        # Add language selection argument
        parser.add_argument(
            "--lang",
            choices=["en", "de"],
            default="en",
            help="Language for reminder messages (en=English, de=German)"
        )

    def execute(self, args):
        # Set the language to use
        self.lang = args.lang

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Handle startup configuration if provided
            if hasattr(args, 'startup') and args.startup:
                self._configure_startup_reminder(cursor, args.startup == "enable")
                conn.commit()
                state = self._get_text("startup_enabled" if args.startup == "enable" else "startup_disabled")
                print(state)
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

            # Query 4: Get the current streak information (if gentle mode is enabled)
            streak_length = 0
            if args.gentle and not args.force:  # Only calculate streak if needed
                streak_length = self._get_current_streak(cursor)

            # Determine user activity status for today
            has_activity_today = words_added_today > 0 or reviews_today > 0

            # Check if we should show a reminder in gentle mode
            if args.gentle and not args.force and (has_activity_today or streak_length <= 1):
                # In gentle mode, don't show anything if user has already practiced
                # or if their streak is 0 or 1 day (not at risk)
                print(self._get_text("gentle_no_reminder"))
                return

            # Generate and display the appropriate message, and log it
            # Note: with --force, we'll show a message regardless of activity status

            if has_activity_today and not args.force:
                # Normal positive message for active users (unless forced)
                message = self._show_positive_message(
                    words_added_today, reviews_done=reviews_today,
                    time_of_day=args.time, daily_goal=daily_goal,
                    custom_message=args.custom_message
                )
                self._log_reminder(cursor, "positive", message)
            else:
                # If in gentle mode and streak > 1, or if force flag is used
                if (args.gentle and streak_length > 1) or args.force:
                    # Choose appropriate message type based on context
                    if args.force and has_activity_today:
                        # Force flag with activity - show positive but mark as forced
                        message = self._show_positive_message(
                            words_added_today, reviews_done=reviews_today,
                            time_of_day=args.time, daily_goal=daily_goal,
                            custom_message=args.custom_message, forced=True
                        )
                        self._log_reminder(cursor, "forced_positive", message)
                    elif args.force:
                        # Force flag without activity - show reminder but mark as forced
                        message = self._show_reminder_message(
                            time_of_day=args.time, daily_goal=daily_goal,
                            custom_message=args.custom_message, forced=True
                        )
                        self._log_reminder(cursor, "forced_reminder", message)
                    elif args.gentle:
                        # Gentle mode with streak at risk
                        message = self._show_streak_at_risk_message(
                            streak_length, time_of_day=args.time,
                            daily_goal=daily_goal, custom_message=args.custom_message
                        )
                        self._log_reminder(cursor, "streak_risk", message)
                else:
                    # Standard reminder message
                    message = self._show_reminder_message(
                        time_of_day=args.time, daily_goal=daily_goal,
                        custom_message=args.custom_message
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

    def _get_text(self, key, **kwargs):
        """Get translated text from the language dictionary with placeholders filled."""
        if key not in self.TRANSLATIONS[self.lang]:
            # Fall back to English if the key doesn't exist in the selected language
            value = self.TRANSLATIONS["en"].get(key, f"Missing text key: {key}")
        else:
            value = self.TRANSLATIONS[self.lang][key]

        # If the value is a list, pick a random item
        if isinstance(value, list):
            value = random.choice(value)

        # Fill in any placeholders
        if kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError:
                # Just return the original string if placeholders don't match
                pass

        return value

    def _get_current_streak(self, cursor):
        """Calculate the current learning streak from activity records."""
        try:
            # Initialize streak counter
            streak_days = 0
            current_date = datetime.datetime.now().date()

            # Start checking from yesterday (since today is checked separately)
            check_date = current_date - datetime.timedelta(days=1)

            # We'll check up to 1000 days back to avoid infinite loops
            # This is just a safety measure - practical streaks won't be this long
            for _ in range(1000):
                date_str = check_date.isoformat()
                has_activity = False

                # Check for word additions on this date
                cursor.execute(
                    "SELECT COUNT(*) FROM words WHERE date_added LIKE ?",
                    (f"{date_str}%",)
                )
                if cursor.fetchone()[0] > 0:
                    has_activity = True

                # Check for reviews on this date if we have review records
                if not has_activity:
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='review_sessions'"
                    )
                    if cursor.fetchone():
                        cursor.execute(
                            "SELECT COUNT(*) FROM review_sessions WHERE session_date LIKE ?",
                            (f"{date_str}%",)
                        )
                        if cursor.fetchone()[0] > 0:
                            has_activity = True
                    else:
                        # Fall back to last_review_date in words table
                        cursor.execute(
                            "SELECT COUNT(*) FROM pragma_table_info('words') WHERE name='last_review_date'"
                        )
                        if cursor.fetchone()[0] > 0:
                            cursor.execute(
                                "SELECT COUNT(*) FROM words WHERE last_review_date LIKE ?",
                                (f"{date_str}%",)
                            )
                            if cursor.fetchone()[0] > 0:
                                has_activity = True

                # If no activity found for this day, streak ends
                if not has_activity:
                    break

                # Otherwise, increment streak and check previous day
                streak_days += 1
                check_date = check_date - datetime.timedelta(days=1)

            return streak_days
        except sqlite3.Error:
            # In case of database error, return 0 (no streak)
            return 0

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
            return self._get_text("goal_achieved", words_added=words_added_today,
                                  daily_goal=daily_goal, percentage=percentage)
        else:
            return self._get_text("goal_progress", words_added=words_added_today,
                                  daily_goal=daily_goal, percentage=percentage)

    def _show_streak_at_risk_message(self, streak_length, time_of_day=None, daily_goal=None, custom_message=None):
        """Display a reminder focusing on the streak being at risk."""
        # Determine the main message (custom or default)
        if custom_message:
            main_message = f"✨ {custom_message}"
        else:
            # Get the streak message with the streak length formatted in
            main_message = "⚠️ " + self._get_text("streak_risk", streak_length=streak_length)

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
        if time_of_day == "morning":
            suggestion_message = self._get_text("streak_suggestion_morning")
        elif time_of_day == "evening":
            suggestion_message = self._get_text("streak_suggestion_evening")
        else:
            suggestion_message = self._get_text("streak_suggestion_default")

        print(f"{suggestion_message}\n")
        full_message += f"{suggestion_message}"

        return full_message

    def _show_positive_message(self, words_added, reviews_done, time_of_day=None, daily_goal=None, custom_message=None,
                               forced=False):
        """Display a positive reinforcement message, optionally customized."""
        # Determine the main message (custom or default)
        if custom_message:
            main_message = f"✨ {custom_message}"
        else:
            # Select the appropriate message category based on time of day
            if time_of_day == "morning":
                message_type = "positive_morning"
            elif time_of_day == "evening":
                message_type = "positive_evening"
            else:
                message_type = "positive_default"

            # Get a random message from the appropriate category
            message = self._get_text(message_type)

            # Add forced indicator if applicable
            if forced:
                forced_suffix = self._get_text("forced_reminder_suffix")
                main_message = f"🔔 {message} {forced_suffix}"
            else:
                main_message = f"🎉 {message}"

        # Print the main message
        print(f"\n{main_message}")

        # Build the full message for logging
        full_message = main_message

        # Add activity details
        activity_message = ""
        if words_added > 0 and reviews_done > 0:
            activity_message = self._get_text("activity_added_reviewed",
                                              words_added=words_added, reviews_done=reviews_done)
        elif words_added > 0:
            activity_message = self._get_text("activity_added", words_added=words_added)
        elif reviews_done > 0:
            activity_message = self._get_text("activity_reviewed", reviews_done=reviews_done)

        if activity_message:
            print(activity_message)
            full_message += f"\n{activity_message}"

        # Add goal progress if a goal is set
        if daily_goal:
            goal_message = self._format_goal_progress(words_added, daily_goal)
            print(goal_message)
            full_message += goal_message

        # Add a suggestion based on time of day
        if time_of_day == "morning":
            suggestion_message = self._get_text("suggestion_morning")
        elif time_of_day == "evening":
            suggestion_message = self._get_text("suggestion_evening")
        else:
            suggestion_message = self._get_text("suggestion_default")

        print(f"{suggestion_message}\n")
        full_message += f"{suggestion_message}"

        return full_message

    def _show_reminder_message(self, time_of_day=None, daily_goal=None, custom_message=None, forced=False):
        """Display a motivational reminder message, optionally customized."""
        # Determine the main message (custom or default)
        if custom_message:
            main_message = f"✨ {custom_message}"
        else:
            # Select the appropriate message category based on time of day
            if time_of_day == "morning":
                message_type = "reminder_morning"
            elif time_of_day == "evening":
                message_type = "reminder_evening"
            else:
                message_type = "reminder_default"

            # Get a random message from the appropriate category
            message = self._get_text(message_type)

            # Add forced indicator if applicable
            if forced:
                forced_suffix = self._get_text("forced_reminder_suffix")
                main_message = f"🔔 {message} {forced_suffix}"
            else:
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
        if time_of_day == "morning":
            suggestion_message = self._get_text("reminder_suggestion_morning")
        elif time_of_day == "evening":
            suggestion_message = self._get_text("reminder_suggestion_evening")
        else:
            suggestion_message = self._get_text("reminder_suggestion_default")

        print(f"{suggestion_message}\n")
        full_message += f"{suggestion_message}"

        return full_message