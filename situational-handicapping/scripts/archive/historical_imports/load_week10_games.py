#!/usr/bin/env python3
"""
Load Week 10 2025 NFL games into the database.

Manually adds the Week 10 schedule for testing travel calculations.

Usage:
    python load_week10_games.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

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


def load_week10_games():
    """Load Week 10 2025 games."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if games already exist for Week 10
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = 2025 AND week = 10")
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} games already exist for Week 10, 2025")
        response = input("Delete and reload? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)
        cursor.execute("DELETE FROM games WHERE season = 2025 AND week = 10")
        print(f"✓ Deleted {existing} existing games")

    # Week 10 2025 NFL Schedule (Nov 6-10, 2025)
    # Format: (away_team, home_team, date, time, venue)
    week10_games = [
        ('LV', 'DEN', '2025-11-06', '20:15', 'Empower Field at Mile High'),
        ('ATL', 'IND', '2025-11-09', '09:30', 'Lucas Oil Stadium'),
        ('BAL', 'MIN', '2025-11-09', '13:00', 'U.S. Bank Stadium'),
        ('CLE', 'NYJ', '2025-11-09', '13:00', 'MetLife Stadium'),
        ('NYG', 'CHI', '2025-11-09', '13:00', 'Soldier Field'),
        ('NO', 'CAR', '2025-11-09', '13:00', 'Bank of America Stadium'),
        ('NE', 'TB', '2025-11-09', '13:00', 'Raymond James Stadium'),
        ('BUF', 'MIA', '2025-11-09', '13:00', 'Hard Rock Stadium'),
        ('JAX', 'HOU', '2025-11-09', '13:00', 'NRG Stadium'),
        ('ARI', 'SEA', '2025-11-09', '16:05', 'Lumen Field'),
        ('LAR', 'SF', '2025-11-09', '16:25', "Levi's Stadium"),
        ('DET', 'WSH', '2025-11-09', '16:25', 'Northwest Stadium'),
        ('PIT', 'LAC', '2025-11-09', '20:20', 'SoFi Stadium'),
        ('PHI', 'GB', '2025-11-10', '20:15', 'Lambeau Field'),
    ]

    inserted = 0
    for away_abbr, home_abbr, date, time, venue in week10_games:
        try:
            away_id = get_team_id(cursor, away_abbr)
            home_id = get_team_id(cursor, home_abbr)

            cursor.execute("""
                INSERT INTO games (season, week, game_date, game_time,
                                 home_team_id, away_team_id, venue)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [2025, 10, date, time, home_id, away_id, venue])

            inserted += 1
            print(f"  ✓ Week 10: {away_abbr} @ {home_abbr} ({date})")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue

    conn.commit()
    print(f"\n✅ Successfully loaded {inserted} Week 10 games")

    # Show summary
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN game_date = '2025-11-06' THEN 1 END) as thursday,
               COUNT(CASE WHEN game_date = '2025-11-09' THEN 1 END) as sunday,
               COUNT(CASE WHEN game_date = '2025-11-10' THEN 1 END) as monday
        FROM games
        WHERE season = 2025 AND week = 10
    """)

    total, thursday, sunday, monday = cursor.fetchone()
    print(f"\nWeek 10 Schedule Summary:")
    print(f"  Thursday night: {thursday}")
    print(f"  Sunday games: {sunday}")
    print(f"  Monday night: {monday}")
    print(f"  Total: {total}")

    conn.close()


if __name__ == "__main__":
    try:
        load_week10_games()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
