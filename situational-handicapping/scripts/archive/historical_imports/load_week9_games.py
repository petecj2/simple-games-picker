#!/usr/bin/env python3
"""
Load Week 9 2025 NFL games into the database.

Manually adds the Week 9 schedule for testing travel calculations.

Usage:
    python load_week9_games.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"


def get_team_id(cursor, abbr):
    """Get team_id for a team abbreviation."""
    cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [abbr])
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Team not found: {abbr}")
    return result[0]


def load_week9_games():
    """Load Week 9 2025 games."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if games already exist for Week 9
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = 2025 AND week = 9")
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} games already exist for Week 9, 2025")
        response = input("Delete and reload? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)
        cursor.execute("DELETE FROM games WHERE season = 2025 AND week = 9")
        print(f"✓ Deleted {existing} existing games")

    # Week 9 2025 NFL Schedule (Nov 2-4, 2025)
    # Format: (away_team, home_team, date, time, venue)
    week9_games = [
        ('BAL', 'DEN', '2025-11-03', '13:00', 'Empower Field at Mile High'),
        ('LV', 'CIN', '2025-11-03', '13:00', 'Paycor Stadium'),
        ('LAC', 'CLE', '2025-11-03', '13:00', 'Cleveland Browns Stadium'),
        ('NE', 'TEN', '2025-11-03', '13:00', 'Nissan Stadium'),
        ('WSH', 'NYG', '2025-11-03', '13:00', 'MetLife Stadium'),
        ('NO', 'CAR', '2025-11-03', '13:00', 'Bank of America Stadium'),
        ('MIA', 'BUF', '2025-11-03', '13:00', 'Highmark Stadium'),
        ('IND', 'MIN', '2025-11-03', '13:00', 'U.S. Bank Stadium'),
        ('ATL', 'DAL', '2025-11-03', '13:00', 'AT&T Stadium'),
        ('CHI', 'ARI', '2025-11-03', '16:05', 'State Farm Stadium'),
        ('DET', 'GB', '2025-11-03', '16:25', 'Lambeau Field'),
        ('LAR', 'SEA', '2025-11-03', '16:25', 'Lumen Field'),
        ('TB', 'KC', '2025-11-04', '20:20', 'GEHA Field at Arrowhead Stadium'),
    ]

    inserted = 0
    for away_abbr, home_abbr, date, time, venue in week9_games:
        try:
            away_id = get_team_id(cursor, away_abbr)
            home_id = get_team_id(cursor, home_abbr)

            cursor.execute("""
                INSERT INTO games (season, week, game_date, game_time,
                                 home_team_id, away_team_id, venue)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [2025, 9, date, time, home_id, away_id, venue])

            inserted += 1
            print(f"  ✓ Week 9: {away_abbr} @ {home_abbr} ({date})")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue

    conn.commit()
    print(f"\n✅ Successfully loaded {inserted} Week 9 games")

    # Show summary
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN game_date = '2025-11-03' THEN 1 END) as sunday,
               COUNT(CASE WHEN game_date = '2025-11-04' THEN 1 END) as monday
        FROM games
        WHERE season = 2025 AND week = 9
    """)

    total, sunday, monday = cursor.fetchone()
    print(f"\nWeek 9 Schedule Summary:")
    print(f"  Sunday games: {sunday}")
    print(f"  Monday night: {monday}")
    print(f"  Total: {total}")

    conn.close()


if __name__ == "__main__":
    try:
        load_week9_games()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
