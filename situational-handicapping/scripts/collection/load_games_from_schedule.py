#!/usr/bin/env python3
"""
Generic script to load NFL game schedules into the database.

Supports multiple data sources:
- ESPN API (automated, real-time)
- CSV file (manual entry)
- Markdown file (from existing predictions)

Usage:
    # Load from ESPN API (preferred)
    python load_games_from_schedule.py --season 2025 --week 11 --source espn

    # Load from CSV file
    python load_games_from_schedule.py --season 2025 --week 11 --source csv --file data/schedule_week11.csv

    # Load from markdown predictions file
    python load_games_from_schedule.py --season 2025 --week 11 --source markdown --file data/week11_predictions.md

    # Load full season from ESPN
    python load_games_from_schedule.py --season 2025 --source espn
"""

import argparse
import csv
import json
import re
import sqlite3
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"

# ESPN API endpoint
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Team name to abbreviation mapping
TEAM_NAME_TO_ABBR = {
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


def get_team_id(cursor, abbr):
    """Get team_id for a team abbreviation."""
    cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [abbr])
    result = cursor.fetchone()
    if result:
        return result[0]

    # Try common abbreviation mappings
    abbr_map = {
        'WSH': 'WSH',  # Washington Commanders
        'WAS': 'WSH',
        'JAC': 'JAX',  # Jacksonville
        'LAR': 'LAR',  # LA Rams
        'LA': 'LAR',
    }

    mapped = abbr_map.get(abbr)
    if mapped:
        cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [mapped])
        result = cursor.fetchone()
        if result:
            return result[0]

    raise ValueError(f"Team not found: {abbr}")


def fetch_schedule_from_espn(season, week=None):
    """Fetch schedule from ESPN API."""
    games = []

    if week:
        weeks = [week]
    else:
        # NFL regular season is weeks 1-18
        weeks = range(1, 19)

    # Create SSL context that doesn't verify certificates (for development)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for wk in weeks:
        url = f"{ESPN_API_BASE}?league=nfl&season={season}&seasontype=2&week={wk}"

        try:
            print(f"Fetching Week {wk} schedule from ESPN...")

            with urllib.request.urlopen(url, context=ssl_context, timeout=10) as response:
                data = json.loads(response.read().decode())

            if 'events' not in data:
                print(f"  ⚠️  No games found for Week {wk}")
                continue

            for event in data['events']:
                try:
                    # Extract teams
                    competitions = event['competitions'][0]
                    competitors = competitions['competitors']

                    game_info = {
                        'season': season,
                        'week': wk,
                        'date': event['date'],  # ISO format
                        'venue': competitions.get('venue', {}).get('fullName', ''),
                        'home_team': None,
                        'away_team': None,
                        'home_score': None,
                        'away_score': None
                    }

                    for comp in competitors:
                        team_abbr = comp['team']['abbreviation']
                        if comp['homeAway'] == 'home':
                            game_info['home_team'] = team_abbr
                            if 'score' in comp:
                                game_info['home_score'] = int(comp['score'])
                        else:
                            game_info['away_team'] = team_abbr
                            if 'score' in comp:
                                game_info['away_score'] = int(comp['score'])

                    if game_info['home_team'] and game_info['away_team']:
                        games.append(game_info)

                except (KeyError, IndexError) as e:
                    print(f"  ⚠️  Could not parse game: {e}")
                    continue

            print(f"  ✓ Found {len([g for g in games if g['week'] == wk])} games")

        except urllib.error.URLError as e:
            print(f"  ❌ Error fetching Week {wk}: {e}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error for Week {wk}: {e}")
            continue

    return games


def parse_schedule_from_csv(csv_path, season, week):
    """
    Parse schedule from CSV file.

    Expected CSV format:
    away_team,home_team,date,time,venue
    LV,DEN,2025-11-06,20:15,Empower Field at Mile High
    """
    games = []

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            game = {
                'season': season,
                'week': week,
                'away_team': row['away_team'].strip(),
                'home_team': row['home_team'].strip(),
                'date': row['date'].strip(),
                'time': row.get('time', '').strip(),
                'venue': row.get('venue', '').strip()
            }
            games.append(game)

    print(f"✓ Parsed {len(games)} games from CSV")
    return games


def parse_schedule_from_markdown(md_path, season, week):
    """
    Parse schedule from markdown predictions file.

    Expected format:
    | Date | Time | Away Team | Home Team | ...
    | Thu 10/23 | 8:15PM | Baltimore Ravens | Miami Dolphins | ...
    """
    games = []

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    with open(md_path, 'r') as f:
        content = f.read()

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

            if len(parts) >= 4:
                date_str = parts[0]
                time_str = parts[1]
                away_team = parts[2]
                home_team = parts[3]

                # Convert team names to abbreviations
                away_abbr = TEAM_NAME_TO_ABBR.get(away_team, away_team)
                home_abbr = TEAM_NAME_TO_ABBR.get(home_team, home_team)

                # Parse date and time
                game_date, game_time = parse_markdown_date_time(date_str, time_str, season)

                game = {
                    'season': season,
                    'week': week,
                    'away_team': away_abbr,
                    'home_team': home_abbr,
                    'date': game_date,
                    'time': game_time,
                    'venue': ''
                }
                games.append(game)

    print(f"✓ Parsed {len(games)} games from markdown")
    return games


def parse_markdown_date_time(date_str, time_str, season):
    """Parse date and time strings from markdown format."""
    # Date format: "Thu 10/23" or "Sun 10/26"
    # Time format: "8:15PM" or "1:00PM"

    # Extract month and day
    date_match = re.search(r'(\d+)/(\d+)', date_str)
    if not date_match:
        raise ValueError(f"Could not parse date: {date_str}")

    month = int(date_match.group(1))
    day = int(date_match.group(2))

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

    game_date = f"{season}-{month:02d}-{day:02d}"
    game_time = f"{hour:02d}:{minute:02d}"

    return game_date, game_time


def load_games_into_database(games, overwrite=False):
    """Load games into the database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not games:
        print("❌ No games to load")
        conn.close()
        return

    # Get season and week from first game
    season = games[0]['season']
    week = games[0]['week']

    # Check if games already exist
    cursor.execute(
        "SELECT COUNT(*) FROM games WHERE season = ? AND week = ?",
        [season, week]
    )
    existing = cursor.fetchone()[0]

    if existing > 0:
        if overwrite:
            cursor.execute(
                "DELETE FROM games WHERE season = ? AND week = ?",
                [season, week]
            )
            print(f"✓ Deleted {existing} existing games for Week {week}")
        else:
            print(f"⚠️  Warning: {existing} games already exist for Week {week}, {season}")
            response = input("Delete and reload? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                conn.close()
                sys.exit(0)
            cursor.execute(
                "DELETE FROM games WHERE season = ? AND week = ?",
                [season, week]
            )
            print(f"✓ Deleted {existing} existing games")

    # Insert games
    print(f"\nLoading {len(games)} games into database...")
    inserted = 0

    for game in games:
        try:
            away_id = get_team_id(cursor, game['away_team'])
            home_id = get_team_id(cursor, game['home_team'])

            # Parse date and time
            if isinstance(game['date'], str):
                # Handle both ISO format (from ESPN) and YYYY-MM-DD format
                if 'T' in game['date']:
                    game_dt = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                    game_date = game_dt.strftime('%Y-%m-%d')
                    game_time = game_dt.strftime('%H:%M')
                else:
                    game_date = game['date']
                    game_time = game.get('time', '00:00')

            cursor.execute("""
                INSERT INTO games (season, week, game_date, game_time,
                                 home_team_id, away_team_id, venue,
                                 home_score, away_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                game['season'], game['week'], game_date, game_time,
                home_id, away_id, game.get('venue', ''),
                game.get('home_score'), game.get('away_score')
            ])

            inserted += 1
            print(f"  ✓ Week {week}: {game['away_team']} @ {game['home_team']} ({game_date})")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            continue

    conn.commit()
    print(f"\n✅ Successfully loaded {inserted} games for Week {week}, {season}")

    # Show summary
    cursor.execute("""
        SELECT DATE(game_date) as date, COUNT(*) as count
        FROM games
        WHERE season = ? AND week = ?
        GROUP BY DATE(game_date)
        ORDER BY DATE(game_date)
    """, [season, week])

    print(f"\nWeek {week} Schedule Summary:")
    for date, count in cursor.fetchall():
        print(f"  {date}: {count} game(s)")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Load NFL game schedules from multiple sources'
    )
    parser.add_argument(
        '--season', type=int, required=True,
        help='NFL season year (e.g., 2025)'
    )
    parser.add_argument(
        '--week', type=int,
        help='Week number (optional for ESPN source)'
    )
    parser.add_argument(
        '--source', type=str, required=True,
        choices=['espn', 'csv', 'markdown'],
        help='Data source: espn (API), csv (file), or markdown (predictions file)'
    )
    parser.add_argument(
        '--file', type=str,
        help='Path to CSV or markdown file (required for csv/markdown sources)'
    )
    parser.add_argument(
        '--overwrite', action='store_true',
        help='Overwrite existing games without prompting'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.source in ['csv', 'markdown'] and not args.file:
        parser.error(f"--file is required when using --source {args.source}")

    if args.source in ['csv', 'markdown'] and not args.week:
        parser.error(f"--week is required when using --source {args.source}")

    try:
        # Load games based on source
        if args.source == 'espn':
            games = fetch_schedule_from_espn(args.season, args.week)
        elif args.source == 'csv':
            file_path = Path(args.file)
            games = parse_schedule_from_csv(file_path, args.season, args.week)
        elif args.source == 'markdown':
            file_path = Path(args.file)
            games = parse_schedule_from_markdown(file_path, args.season, args.week)

        if not games:
            print("❌ No games found")
            sys.exit(1)

        # Load into database
        load_games_into_database(games, args.overwrite)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
