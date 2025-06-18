import sqlite3
import datetime

def ensure_goals_table(conn):
    """Ensure the goals table exists in the database."""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value INTEGER NOT NULL
    )
    ''')
    conn.commit()


def get_goal_value(conn, key):
    """Get a goal value by key from the database.

    Args:
        conn (sqlite3.Connection): Database connection
        key (str): Goal key (e.g., 'daily_word_goal')

    Returns:
        int or None: The goal value or None if not found
    """
    ensure_goals_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    return int(result[0]) if result else None


def set_goal_value(conn, key, value):
    """Set a goal value in the database.

    Args:
        conn (sqlite3.Connection): Database connection
        key (str): Goal key (e.g., 'daily_word_goal')
        value (int): Goal value to store

    Returns:
        bool: True if a new goal was created, False if updated
    """
    ensure_goals_table(conn)
    cursor = conn.cursor()

    # Check if a goal with this key already exists
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE settings SET value = ? WHERE key = ?",
            (value, key)
        )
        conn.commit()
        return False  # Updated existing
    else:
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        return True  # Created new


def delete_goal(conn, key):
    """Delete a goal from the database.

    Args:
        conn (sqlite3.Connection): Database connection
        key (str): Goal key to delete

    Returns:
        bool: True if goal was deleted, False if not found
    """
    ensure_goals_table(conn)
    cursor = conn.cursor()

    # Check if goal exists
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return True  # Deleted successfully
    else:
        return False  # No goal found


def ensure_streaks_table(conn):
    """Ensure the streaks table exists in the database."""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS streaks (
        date TEXT PRIMARY KEY,
        goal_met BOOLEAN NOT NULL
    )
    ''')
    conn.commit()


def record_streak(conn, date, goal_met):
    """Record whether the goal was met on a specific date.

    Args:
        conn (sqlite3.Connection): Database connection
        date (str): Date in ISO format (YYYY-MM-DD)
        goal_met (bool): Whether the goal was met

    Returns:
        bool: True if a new record was created, False if updated
    """
    ensure_streaks_table(conn)
    cursor = conn.cursor()

    # Check if a record for this date already exists
    cursor.execute("SELECT goal_met FROM streaks WHERE date = ?", (date,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE streaks SET goal_met = ? WHERE date = ?",
            (goal_met, date)
        )
        conn.commit()
        return False  # Updated existing
    else:
        cursor.execute(
            "INSERT INTO streaks (date, goal_met) VALUES (?, ?)",
            (date, goal_met)
        )
        conn.commit()
        return True  # Created new


def calculate_current_streak(conn, today=None):
    """Calculate the current streak of consecutive days where the goal was met.

    Args:
        conn (sqlite3.Connection): Database connection
        today (str, optional): Today's date in ISO format. If None, today's date is used.

    Returns:
        int: Number of consecutive days the goal was met (0 if no streak).
    """
    if today is None:
        today = datetime.date.today().isoformat()

    ensure_streaks_table(conn)
    cursor = conn.cursor()

    # Get all streaks ordered by date in descending order (most recent first)
    cursor.execute(
        "SELECT date, goal_met FROM streaks WHERE date <= ? ORDER BY date DESC",
        (today,)
    )
    streak_records = cursor.fetchall()

    if not streak_records:
        return 0  # No streaks recorded

    # Calculate current streak (consecutive days with goal_met = True)
    streak_count = 0
    prev_date = None

    for date_str, goal_met in streak_records:
        # Convert string date to date object for comparison
        current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        # Handle the first record
        if prev_date is None:
            if goal_met:  # If the most recent record shows goal was met
                streak_count = 1
                prev_date = current_date
            else:
                return 0  # Most recent record shows goal was not met, no current streak
            continue

        # Calculate the expected date (one day before previous date)
        expected_date = prev_date - datetime.timedelta(days=1)

        # Check if this record is consecutive and goal was met
        if current_date == expected_date and goal_met:
            streak_count += 1
            prev_date = current_date
        else:
            # Chain is broken
            break

    return streak_count