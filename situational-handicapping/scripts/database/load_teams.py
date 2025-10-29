#!/usr/bin/env python3
"""
Load teams from stadium_coordinates.json into the database.

Reads the stadium coordinates JSON file and populates the teams table
with all 32 NFL teams including stadium locations and timezone information.

Usage:
    python load_teams.py
"""

import json
import sqlite3
import sys
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"
COORDS_PATH = DATA_DIR / "stadium_coordinates.json"


def load_teams():
    """Load teams from JSON into database."""
    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    # Check if stadium coordinates file exists
    if not COORDS_PATH.exists():
        print(f"❌ Stadium coordinates file not found: {COORDS_PATH}")
        sys.exit(1)

    # Load stadium coordinates
    with open(COORDS_PATH, 'r') as f:
        data = json.load(f)

    teams = data['teams']
    print(f"Loaded {len(teams)} teams from {COORDS_PATH}")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if teams already exist
    cursor.execute("SELECT COUNT(*) FROM teams")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        print(f"\n⚠️  Warning: {existing_count} teams already in database")
        response = input("Delete existing teams and reload? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)

        # Delete existing teams
        cursor.execute("DELETE FROM teams")
        print("✓ Deleted existing teams")

    # Insert teams
    inserted = 0
    for abbr, team_data in teams.items():
        cursor.execute("""
            INSERT INTO teams (abbreviation, name, division, conference,
                             stadium_name, stadium_lat, stadium_lon, timezone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            abbr,
            team_data['name'],
            team_data['division'],
            team_data['conference'],
            team_data['stadium'],
            team_data['latitude'],
            team_data['longitude'],
            team_data['timezone']
        ])
        inserted += 1
        print(f"  ✓ {abbr}: {team_data['name']}")

    conn.commit()

    print(f"\n✅ Successfully loaded {inserted} teams into database")

    # Show summary by division
    print("\nTeams by Conference/Division:")
    cursor.execute("""
        SELECT conference, division, COUNT(*) as count
        FROM teams
        GROUP BY conference, division
        ORDER BY conference, division
    """)

    for conf, div, count in cursor.fetchall():
        print(f"  {conf} {div}: {count} teams")

    conn.close()


if __name__ == "__main__":
    try:
        load_teams()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
