#!/usr/bin/env python3
"""
Scrape NFL standings from ESPN API.

Fetches current standings including wins, losses, division/conference rank,
and playoff odds for all 32 teams.

Usage:
    python scrape_standings.py --season 2025 --week 9
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
ESPN_STANDINGS_API = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"


def get_team_id(cursor, abbr):
    """Get team_id for a team abbreviation."""
    # Try common abbreviation mappings
    abbr_map = {
        'WSH': 'WSH',
        'WAS': 'WSH',
        'JAC': 'JAX',
        'LAR': 'LAR',
        'LA': 'LAR',
    }

    mapped = abbr_map.get(abbr, abbr)

    cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [mapped])
    result = cursor.fetchone()
    if result:
        return result[0]

    raise ValueError(f"Team not found: {abbr}")


def fetch_standings(season):
    """Fetch standings from ESPN API."""
    url = f"{ESPN_STANDINGS_API}?season={season}"

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        print(f"Fetching standings from ESPN API...")

        with urllib.request.urlopen(url, context=ssl_context) as response:
            data = json.loads(response.read().decode())

        standings = []

        # ESPN returns standings by conference and division
        if 'children' not in data:
            print("❌ No standings data found")
            return []

        for conference in data['children']:
            conf_name = conference['abbreviation']  # AFC or NFC

            for division in conference['standings']['entries']:
                team = division['team']
                stats = division['stats']

                # Extract stats by name
                stat_values = {}
                for stat in stats:
                    stat_values[stat['name']] = stat['value']

                team_data = {
                    'abbreviation': team['abbreviation'],
                    'name': team['displayName'],
                    'conference': conf_name,
                    'wins': int(stat_values.get('wins', 0)),
                    'losses': int(stat_values.get('losses', 0)),
                    'ties': int(stat_values.get('ties', 0)),
                    'win_pct': float(stat_values.get('winPercent', 0)),
                    'points_for': int(stat_values.get('pointsFor', 0)),
                    'points_against': int(stat_values.get('pointsAgainst', 0)),
                    'streak': stat_values.get('streak', ''),
                    'division_record': stat_values.get('divisionwinpercent', ''),
                }

                standings.append(team_data)

        print(f"  Found standings for {len(standings)} teams")
        return standings

    except urllib.error.URLError as e:
        print(f"❌ Error fetching standings: {e}")
        return []
    except (KeyError, json.JSONDecodeError) as e:
        print(f"❌ Error parsing standings data: {e}")
        return []


def calculate_division_ranks(standings_data):
    """Calculate division ranks for each team."""
    # Group by division
    divisions = {}
    for team in standings_data:
        # Get division from database
        key = (team['conference'], team.get('division', ''))
        if key not in divisions:
            divisions[key] = []
        divisions[key].append(team)

    # Rank within each division
    for div_teams in divisions.values():
        # Sort by wins (descending), then losses (ascending)
        div_teams.sort(key=lambda x: (-x['wins'], x['losses']))

        for rank, team in enumerate(div_teams, 1):
            team['division_rank'] = rank

            # Calculate games behind leader
            if rank == 1:
                team['games_behind'] = 0.0
            else:
                leader = div_teams[0]
                gb = ((leader['wins'] - team['wins']) + (team['losses'] - leader['losses'])) / 2.0
                team['games_behind'] = gb


def calculate_conference_ranks(standings_data):
    """Calculate conference ranks for each team."""
    # Group by conference
    conferences = {'AFC': [], 'NFC': []}
    for team in standings_data:
        conf = team['conference']
        if conf in conferences:
            conferences[conf].append(team)

    # Rank within each conference
    for conf_teams in conferences.values():
        conf_teams.sort(key=lambda x: (-x['wins'], x['losses']))

        for rank, team in enumerate(conf_teams, 1):
            team['conference_rank'] = rank


def load_standings(season, week):
    """Load standings into database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch team divisions from database
    cursor.execute("SELECT abbreviation, division, conference FROM teams")
    team_divisions = {row[0]: {'division': row[1], 'conference': row[2]} for row in cursor.fetchall()}

    # Fetch standings from ESPN
    standings_data = fetch_standings(season)

    if not standings_data:
        print("❌ No standings data to load")
        conn.close()
        sys.exit(1)

    # Add division info from our database
    for team in standings_data:
        abbr = team['abbreviation']
        if abbr in team_divisions:
            team['division'] = team_divisions[abbr]['division']
            team['conference'] = team_divisions[abbr]['conference']

    # Calculate ranks
    calculate_division_ranks(standings_data)
    calculate_conference_ranks(standings_data)

    # Check if standings already exist for this week
    cursor.execute("SELECT COUNT(*) FROM standings WHERE season = ? AND week = ?", [season, week])
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: Standings already exist for Week {week}, {season}")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            conn.close()
            sys.exit(0)

        cursor.execute("DELETE FROM standings WHERE season = ? AND week = ?", [season, week])
        print(f"✓ Deleted {existing} existing standings records")

    # Insert standings
    print(f"\nLoading standings for Week {week}, {season}...")
    inserted = 0

    for team in standings_data:
        try:
            team_id = get_team_id(cursor, team['abbreviation'])

            # Estimate playoff odds (ESPN doesn't provide this directly in standings)
            # Simple heuristic: teams with winning records have higher odds
            win_pct = team['win_pct']
            if win_pct >= 0.750:
                playoff_odds = 95.0
            elif win_pct >= 0.625:
                playoff_odds = 75.0
            elif win_pct >= 0.500:
                playoff_odds = 50.0
            elif win_pct >= 0.375:
                playoff_odds = 25.0
            else:
                playoff_odds = 5.0

            cursor.execute("""
                INSERT INTO standings (team_id, season, week, wins, losses, ties,
                                     division_rank, conference_rank, playoff_odds, games_behind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                team_id, season, week,
                team['wins'], team['losses'], team['ties'],
                team['division_rank'], team['conference_rank'],
                playoff_odds, team['games_behind']
            ])

            inserted += 1

        except ValueError as e:
            print(f"  ❌ Error: {e} - {team.get('name', 'Unknown team')}")
            continue
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            continue

    conn.commit()

    print(f"\n✅ Loaded standings for {inserted} teams")

    # Show summary by division
    print(f"\nWeek {week} Standings Summary:")

    for conf in ['AFC', 'NFC']:
        print(f"\n{conf}:")
        cursor.execute("""
            SELECT t.abbreviation, s.wins, s.losses, s.division_rank, t.division
            FROM standings s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.season = ? AND s.week = ? AND t.conference = ?
            ORDER BY t.division, s.division_rank
        """, [season, week, conf])

        current_div = None
        for abbr, wins, losses, rank, div in cursor.fetchall():
            if div != current_div:
                print(f"  {div}:")
                current_div = div
            print(f"    {rank}. {abbr}: {wins}-{losses}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Scrape NFL standings from ESPN')
    parser.add_argument('--season', type=int, required=True, help='NFL season year (e.g., 2025)')
    parser.add_argument('--week', type=int, required=True, help='Week number for standings')

    args = parser.parse_args()

    try:
        load_standings(args.season, args.week)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
