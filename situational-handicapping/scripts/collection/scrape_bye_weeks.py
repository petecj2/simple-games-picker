#!/usr/bin/env python3
"""
Scrape NFL bye weeks from ESPN API.

Determines which teams have bye weeks by analyzing the schedule and finding
weeks where teams don't play.

Usage:
    python scrape_bye_weeks.py --season 2025
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
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
    abbr_map = {
        'WSH': 'WSH',
        'WAS': 'WSH',
        'JAC': 'JAX',
        'LAR': 'LAR',
        'LA': 'LAR',
    }

    mapped = abbr_map.get(abbr, abbr)

    cursor.execute("SELECT team_id, name FROM teams WHERE abbreviation = ?", [mapped])
    result = cursor.fetchone()
    if result:
        return result[0], result[1]

    raise ValueError(f"Team not found: {abbr}")


def find_bye_weeks(season):
    """
    Find bye weeks by analyzing schedule.

    Returns a dict mapping team abbreviation to bye week number.
    """
    print(f"Analyzing {season} schedule to find bye weeks...")

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Track which teams play each week
    teams_playing = {}  # week -> set of team abbreviations

    for week in range(1, 19):  # Weeks 1-18
        url = f"{ESPN_API_BASE}?league=nfl&season={season}&seasontype=2&week={week}"

        try:
            with urllib.request.urlopen(url, context=ssl_context) as response:
                data = json.loads(response.read().decode())

            teams_playing[week] = set()

            if 'events' in data:
                for event in data['events']:
                    try:
                        competitors = event['competitions'][0]['competitors']
                        for comp in competitors:
                            team_abbr = comp['team']['abbreviation']
                            teams_playing[week].add(team_abbr)
                    except (KeyError, IndexError):
                        continue

            print(f"  Week {week}: {len(teams_playing[week])} teams playing")

        except urllib.error.URLError as e:
            print(f"  Warning: Could not fetch Week {week}: {e}")
            teams_playing[week] = set()

    # Get all teams
    all_teams = set()
    for teams in teams_playing.values():
        all_teams.update(teams)

    print(f"\nFound {len(all_teams)} teams total")

    # Find bye weeks for each team
    bye_weeks = {}
    for team in sorted(all_teams):
        for week in range(1, 19):
            if week in teams_playing and team not in teams_playing[week]:
                # Check if this is a real bye (not just missing data)
                # A team should play in adjacent weeks
                played_before = any(team in teams_playing.get(w, set()) for w in range(1, week))
                played_after = any(team in teams_playing.get(w, set()) for w in range(week + 1, 19))

                if played_before and played_after:
                    bye_weeks[team] = week
                    break

    return bye_weeks


def load_bye_weeks(season):
    """Load bye weeks into database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if bye weeks already exist
    cursor.execute("SELECT COUNT(*) FROM bye_weeks WHERE season = ?", [season])
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} bye week records already exist for {season}")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)

        cursor.execute("DELETE FROM bye_weeks WHERE season = ?", [season])
        print(f"✓ Deleted {existing} existing bye week records")

    # Find bye weeks from schedule
    bye_weeks = find_bye_weeks(season)

    if not bye_weeks:
        print("❌ No bye weeks found")
        conn.close()
        sys.exit(1)

    # Insert bye weeks
    print(f"\nLoading bye weeks into database...")
    inserted = 0

    # VSiN historical ATS data for teams coming off bye
    # These are general stats, not team-specific
    historical_ats = "32-16 (66.7%)"  # Road favorites after bye vs divisional
    sample_size = 48

    for team_abbr, bye_week in sorted(bye_weeks.items()):
        try:
            team_id, team_name = get_team_id(cursor, team_abbr)

            cursor.execute("""
                INSERT INTO bye_weeks (team_id, season, bye_week_number,
                                     historical_ats_record, historical_sample_size)
                VALUES (?, ?, ?, ?, ?)
            """, [team_id, season, bye_week, historical_ats, sample_size])

            inserted += 1
            print(f"  ✓ {team_abbr} ({team_name}): Week {bye_week}")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            continue

    conn.commit()

    print(f"\n✅ Loaded {inserted} bye weeks")

    # Show summary by week
    cursor.execute("""
        SELECT b.bye_week_number, COUNT(*) as count
        FROM bye_weeks b
        WHERE b.season = ?
        GROUP BY b.bye_week_number
        ORDER BY b.bye_week_number
    """, [season])

    print(f"\nBye Week Distribution:")
    for week, count in cursor.fetchall():
        cursor.execute("""
            SELECT t.abbreviation
            FROM bye_weeks b
            JOIN teams t ON b.team_id = t.team_id
            WHERE b.season = ? AND b.bye_week_number = ?
            ORDER BY t.abbreviation
        """, [season, week])

        teams = [row[0] for row in cursor.fetchall()]
        print(f"  Week {week}: {count} teams ({', '.join(teams)})")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Scrape NFL bye weeks from ESPN')
    parser.add_argument('--season', type=int, required=True, help='NFL season year (e.g., 2025)')

    args = parser.parse_args()

    try:
        load_bye_weeks(args.season)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
