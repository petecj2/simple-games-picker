#!/usr/bin/env python3
"""
Load Week 8 games from week8_predictions.md file.

Parses the markdown table and populates the games table with the actual
Week 8 schedule for situational analysis.

Usage:
    python load_week8_from_predictions.py
"""

import re
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent.parent / "data"
DB_PATH = SCRIPT_DIR.parent.parent / "data" / "nfl_games.db"
PREDICTIONS_FILE = DATA_DIR / "week8_predictions.md"


def get_team_id(cursor, team_name):
    """Get team_id from full team name."""
    # Mapping of full names to abbreviations
    name_to_abbr = {
        'Baltimore Ravens': 'BAL',
        'Miami Dolphins': 'MIA',
        'Atlanta Falcons': 'ATL',
        'New England Patriots': 'NE',
        'Carolina Panthers': 'CAR',
        'Green Bay Packers': 'GB',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Indianapolis Colts': 'IND',
        'Pittsburgh Steelers': 'PIT',
        'Denver Broncos': 'DEN',
        'Houston Texans': 'HOU',
        'Minnesota Vikings': 'MIN',
        'Detroit Lions': 'DET',
        'Los Angeles Chargers': 'LAC',
        'Tennessee Titans': 'TEN',
        'San Francisco 49ers': 'SF',
        'New York Giants': 'NYG',
        'Jacksonville Jaguars': 'JAX',
        'Las Vegas Raiders': 'LV',
        'New Orleans Saints': 'NO',
        'Los Angeles Rams': 'LAR',
        'Kansas City Chiefs': 'KC',
        'Buffalo Bills': 'BUF',
        'Seattle Seahawks': 'SEA',
        'Washington Commanders': 'WSH',
        'Arizona Cardinals': 'ARI',
        'Dallas Cowboys': 'DAL',
        'Cleveland Browns': 'CLE',
        'New York Jets': 'NYJ',
        'Tampa Bay Buccaneers': 'TB',
        'Philadelphia Eagles': 'PHI'
    }

    abbr = name_to_abbr.get(team_name)
    if not abbr:
        raise ValueError(f"Unknown team: {team_name}")

    cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [abbr])
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Team not found in database: {abbr}")

    return result[0]


def parse_date_time(date_str, time_str):
    """Parse date and time strings into database format."""
    # Date format: "Thu 10/23" or "Sun 10/26"
    # Time format: "8:15PM" or "1:00PM"

    # Extract month and day
    date_match = re.search(r'(\d+)/(\d+)', date_str)
    if not date_match:
        raise ValueError(f"Could not parse date: {date_str}")

    month = int(date_match.group(1))
    day = int(date_match.group(2))

    # Determine year (Week 8 is in October)
    year = 2025

    # Parse time
    time_match = re.search(r'(\d+):(\d+)(AM|PM)', time_str)
    if not time_match:
        raise ValueError(f"Could not parse time: {time_str}")

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    meridiem = time_match.group(3)

    # Convert to 24-hour format
    if meridiem == 'PM' and hour != 12:
        hour += 12
    elif meridiem == 'AM' and hour == 12:
        hour = 0

    game_date = f"{year}-{month:02d}-{day:02d}"
    game_time = f"{hour:02d}:{minute:02d}"

    return game_date, game_time


def load_week8_games():
    """Load Week 8 games from predictions markdown file."""
    if not PREDICTIONS_FILE.exists():
        print(f"❌ Predictions file not found: {PREDICTIONS_FILE}")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    # Read predictions file
    with open(PREDICTIONS_FILE, 'r') as f:
        content = f.read()

    # Parse markdown table
    games = []
    in_table = False

    for line in content.split('\n'):
        line = line.strip()

        # Skip header and separator rows
        if line.startswith('| Date |') or line.startswith('|---'):
            in_table = True
            continue

        if in_table and line.startswith('|'):
            # Parse table row
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Skip empty first/last

            if len(parts) >= 7:
                date_str = parts[0]
                time_str = parts[1]
                away_team = parts[2]
                home_team = parts[3]

                games.append({
                    'date_str': date_str,
                    'time_str': time_str,
                    'away_team': away_team,
                    'home_team': home_team
                })

    if not games:
        print("❌ No games found in predictions file")
        sys.exit(1)

    print(f"Found {len(games)} games in predictions file")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if games already exist
    cursor.execute("SELECT COUNT(*) FROM games WHERE season = 2025 AND week = 8")
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} games already exist for Week 8")
        cursor.execute("DELETE FROM games WHERE season = 2025 AND week = 8")
        print(f"✓ Deleted {existing} existing games")

    # Insert games
    print("\nLoading Week 8 games...")
    inserted = 0

    for game in games:
        try:
            away_id = get_team_id(cursor, game['away_team'])
            home_id = get_team_id(cursor, game['home_team'])
            game_date, game_time = parse_date_time(game['date_str'], game['time_str'])

            cursor.execute("""
                INSERT INTO games (season, week, game_date, game_time,
                                 home_team_id, away_team_id, venue)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [2025, 8, game_date, game_time, home_id, away_id, ''])

            inserted += 1
            print(f"  ✓ {game['away_team']} @ {game['home_team']} ({game['date_str']} {game['time_str']})")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue

    conn.commit()
    print(f"\n✅ Successfully loaded {inserted} Week 8 games")

    # Show summary
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN game_date = '2025-10-23' THEN 1 END) as thursday,
               COUNT(CASE WHEN game_date = '2025-10-26' THEN 1 END) as sunday,
               COUNT(CASE WHEN game_date = '2025-10-27' THEN 1 END) as monday
        FROM games
        WHERE season = 2025 AND week = 8
    """)

    total, thursday, sunday, monday = cursor.fetchone()
    print(f"\nWeek 8 Schedule Summary:")
    print(f"  Thursday games: {thursday}")
    print(f"  Sunday games: {sunday}")
    print(f"  Monday games: {monday}")
    print(f"  Total: {total}")

    conn.close()


if __name__ == "__main__":
    try:
        load_week8_games()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
