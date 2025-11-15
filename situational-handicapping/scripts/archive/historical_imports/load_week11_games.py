#!/usr/bin/env python3
"""
Load Week 11 2025 NFL games into the database.

Usage:
    python load_week11_games.py
"""

import sqlite3
import sys
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"


def get_team_id(cursor, abbr):
    """Get team_id for a team abbreviation."""
    cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [abbr])
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Team not found: {abbr}")
    return result[0]


def load_week11_games():
    """Load Week 11 2025 games."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if games already exist for Week 11
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = 2025 AND week = 11")
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} games already exist for Week 11, 2025")
        response = input("Delete and reload? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)
        cursor.execute("DELETE FROM games WHERE season = 2025 AND week = 11")
        print(f"✓ Deleted {existing} existing games")

    # Week 11 2025 NFL Schedule (Nov 13-17, 2025)
    # Format: (away_team, home_team, date, time, venue)
    week11_games = [
        ('NYJ', 'NE', '2025-11-13', '20:15', 'Gillette Stadium'),
        ('WSH', 'MIA', '2025-11-16', '09:30', 'Hard Rock Stadium'),
        ('TB', 'BUF', '2025-11-16', '13:00', 'Highmark Stadium'),
        ('GB', 'NYG', '2025-11-16', '13:00', 'MetLife Stadium'),
        ('CHI', 'MIN', '2025-11-16', '13:00', 'U.S. Bank Stadium'),
        ('LAC', 'JAX', '2025-11-16', '13:00', 'EverBank Stadium'),
        ('CAR', 'ATL', '2025-11-16', '13:00', 'Mercedes-Benz Stadium'),
        ('HOU', 'TEN', '2025-11-16', '13:00', 'Nissan Stadium'),
        ('CIN', 'PIT', '2025-11-16', '13:00', 'Acrisure Stadium'),
        ('SF', 'ARI', '2025-11-16', '16:05', 'State Farm Stadium'),
        ('SEA', 'LAR', '2025-11-16', '16:05', 'SoFi Stadium'),
        ('KC', 'DEN', '2025-11-16', '16:25', 'Empower Field at Mile High'),
        ('BAL', 'CLE', '2025-11-16', '16:25', 'Cleveland Browns Stadium'),
        ('DET', 'PHI', '2025-11-16', '20:20', 'Lincoln Financial Field'),
        ('DAL', 'LV', '2025-11-17', '20:15', 'Allegiant Stadium'),
    ]

    inserted = 0
    for away_abbr, home_abbr, date, time, venue in week11_games:
        try:
            away_id = get_team_id(cursor, away_abbr)
            home_id = get_team_id(cursor, home_abbr)

            cursor.execute("""
                INSERT INTO games (season, week, game_date, game_time,
                                 home_team_id, away_team_id, venue)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [2025, 11, date, time, home_id, away_id, venue])

            inserted += 1
            print(f"  ✓ Week 11: {away_abbr} @ {home_abbr} ({date})")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue

    conn.commit()
    print(f"\n✅ Successfully loaded {inserted} Week 11 games")

    # Show summary
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN game_date = '2025-11-13' THEN 1 END) as thursday,
               COUNT(CASE WHEN game_date = '2025-11-16' THEN 1 END) as sunday,
               COUNT(CASE WHEN game_date = '2025-11-17' THEN 1 END) as monday
        FROM games
        WHERE season = 2025 AND week = 11
    """)

    total, thursday, sunday, monday = cursor.fetchone()
    print(f"\nWeek 11 Schedule Summary:")
    print(f"  Thursday night: {thursday}")
    print(f"  Sunday games: {sunday}")
    print(f"  Monday night: {monday}")
    print(f"  Total: {total}")

    conn.close()


if __name__ == "__main__":
    try:
        load_week11_games()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
