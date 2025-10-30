#!/usr/bin/env python3
"""
Scrape NFL schedule from ESPN API for a given season.

Fetches complete season schedule including dates, times, teams, and venues.
Populates the games table in the database.

Usage:
    python scrape_schedule.py --season 2025
    python scrape_schedule.py --season 2025 --week 9
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
import ssl

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"

# ESPN API endpoint
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


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


def fetch_schedule(season, week=None):
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
            print(f"Fetching Week {wk} schedule...")

            with urllib.request.urlopen(url, context=ssl_context) as response:
                data = json.loads(response.read().decode())

            if 'events' not in data:
                print(f"  No games found for Week {wk}")
                continue

            for event in data['events']:
                try:
                    game_info = {
                        'season': season,
                        'week': wk,
                        'game_id': event['id'],
                        'date': event['date'],  # ISO format
                        'name': event['name'],
                        'status': event['status']['type']['name']
                    }

                    # Extract teams
                    competitions = event['competitions'][0]
                    competitors = competitions['competitors']

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

                    # Extract venue
                    if 'venue' in competitions:
                        game_info['venue'] = competitions['venue'].get('fullName', '')

                    # Extract broadcast info
                    if 'broadcasts' in competitions and competitions['broadcasts']:
                        game_info['broadcast'] = competitions['broadcasts'][0].get('names', [''])[0]

                    games.append(game_info)

                except (KeyError, IndexError) as e:
                    print(f"  Warning: Could not parse game: {e}")
                    continue

            print(f"  Found {len([g for g in games if g['week'] == wk])} games")

        except urllib.error.URLError as e:
            print(f"  Error fetching Week {wk}: {e}")
            continue

    return games


def load_schedule(season, week=None, overwrite=False):
    """Load schedule into database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if games already exist
    if week:
        cursor.execute("SELECT COUNT(*) FROM games WHERE season = ? AND week = ?", [season, week])
    else:
        cursor.execute("SELECT COUNT(*) FROM games WHERE season = ?", [season])

    existing = cursor.fetchone()[0]

    if existing > 0 and not overwrite:
        print(f"⚠️  Warning: {existing} games already exist for season {season}" +
              (f" week {week}" if week else ""))
        response = input("Overwrite existing games? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)
        overwrite = True

    if overwrite and existing > 0:
        if week:
            cursor.execute("DELETE FROM games WHERE season = ? AND week = ?", [season, week])
        else:
            cursor.execute("DELETE FROM games WHERE season = ?", [season])
        print(f"✓ Deleted {existing} existing games")

    # Fetch schedule from ESPN
    print(f"\nFetching schedule from ESPN API...")
    games = fetch_schedule(season, week)

    if not games:
        print("❌ No games found")
        conn.close()
        sys.exit(1)

    print(f"\nLoading {len(games)} games into database...")

    inserted = 0
    updated_scores = 0

    for game in games:
        try:
            home_id = get_team_id(cursor, game['home_team'])
            away_id = get_team_id(cursor, game['away_team'])

            # Parse date and time
            game_dt = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
            game_date = game_dt.strftime('%Y-%m-%d')
            game_time = game_dt.strftime('%H:%M')

            # Check if game already exists (by teams and week)
            cursor.execute("""
                SELECT game_id, home_score, away_score
                FROM games
                WHERE season = ? AND week = ? AND home_team_id = ? AND away_team_id = ?
            """, [season, game['week'], home_id, away_id])

            existing_game = cursor.fetchone()

            if existing_game:
                # Update scores if game is complete
                if game.get('status') in ['STATUS_FINAL', 'Final'] and 'home_score' in game:
                    cursor.execute("""
                        UPDATE games
                        SET home_score = ?, away_score = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE game_id = ?
                    """, [game.get('home_score'), game.get('away_score'), existing_game[0]])
                    updated_scores += 1
            else:
                # Insert new game
                cursor.execute("""
                    INSERT INTO games (season, week, game_date, game_time,
                                     home_team_id, away_team_id, venue,
                                     home_score, away_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    season, game['week'], game_date, game_time,
                    home_id, away_id, game.get('venue', ''),
                    game.get('home_score'), game.get('away_score')
                ])
                inserted += 1

            if inserted % 10 == 0 or updated_scores % 10 == 0:
                print(f"  Processed {inserted + updated_scores} games...")

        except ValueError as e:
            print(f"  ❌ Error: {e} - {game.get('name', 'Unknown game')}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            continue

    conn.commit()

    print(f"\n✅ Schedule loaded:")
    print(f"   Inserted: {inserted} games")
    if updated_scores > 0:
        print(f"   Updated scores: {updated_scores} games")

    # Show summary
    cursor.execute("""
        SELECT week, COUNT(*) as count
        FROM games
        WHERE season = ?
        GROUP BY week
        ORDER BY week
    """, [season])

    print(f"\n{season} Season Summary:")
    for wk, count in cursor.fetchall():
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE season = ? AND week = ? AND home_score IS NOT NULL
        """, [season, wk])
        completed = cursor.fetchone()[0]
        status = f"({completed} completed)" if completed > 0 else "(scheduled)"
        print(f"  Week {wk}: {count} games {status}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Scrape NFL schedule from ESPN')
    parser.add_argument('--season', type=int, required=True, help='NFL season year (e.g., 2025)')
    parser.add_argument('--week', type=int, help='Specific week number (optional)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing games without prompting')

    args = parser.parse_args()

    try:
        load_schedule(args.season, args.week, args.overwrite)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
