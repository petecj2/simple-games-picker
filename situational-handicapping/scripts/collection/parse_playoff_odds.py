#!/usr/bin/env python3
"""
Parse playoff odds from NFL.com playoff picture HTML.

Extracts current playoff probability, win probability, and loss probability
for all 32 teams from the saved HTML file and stores them in the database.

Usage:
    python parse_playoff_odds.py playoff_odds.html --season 2025 --week 9
    python parse_playoff_odds.py playoff_odds.html --format json  # Just display, don't save
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from html.parser import HTMLParser

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"


class PlayoffOddsParser(HTMLParser):
    """Parse playoff odds from NFL.com playoff picture page."""

    def __init__(self):
        super().__init__()
        self.teams = []
        self.current_team = None
        self.in_team_container = False
        self.in_team_name = False
        self.in_record = False
        self.in_playoff_section = False
        self.in_prob_label = False
        self.in_prob_value = False
        self.current_label = None
        self.div_depth = 0
        self.classes_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'div':
            self.div_depth += 1
            class_attr = attrs_dict.get('class', '')
            self.classes_stack.append(class_attr)

            # Check for team container
            if 'css-g5y9jx r-1xfd6ze r-18u37iz r-1w6e6rj r-1udh08x r-13qz1uu r-14lw9ot r-zmhlpu' in class_attr:
                self.in_team_container = True
                self.current_team = {
                    'name': None,
                    'abbreviation': None,
                    'record': None,
                    'current_playoff_odds': None,
                    'if_win_playoff_odds': None,
                    'if_lose_playoff_odds': None
                }

            # Check for team name section
            elif self.in_team_container and 'css-146c3p1 r-1khnkhu r-67g43p r-1ui5ee8 r-7abk7p' in class_attr:
                self.in_team_name = True

            # Check for record section
            elif self.in_team_container and 'css-146c3p1 r-1enofrn r-5umb4a' in class_attr:
                self.in_record = True

            # Check for playoff probability section
            elif self.in_team_container and 'css-g5y9jx r-obd0qt r-6koalj r-18u37iz' in class_attr:
                self.in_playoff_section = True

            # Check for probability labels (IF LOSE, CURRENT, IF WIN)
            elif self.in_playoff_section and 'css-146c3p1 r-5umb4a r-1hvymac r-1armvtb r-1uws2sx' in class_attr:
                self.in_prob_label = True

            # Check for probability values (percentages)
            elif self.in_playoff_section and 'css-146c3p1 r-5umb4a r-67g43p r-1b43r93 r-13hhlc' in class_attr:
                self.in_prob_value = True

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.classes_stack:
                popped_class = self.classes_stack.pop()

                # End of team container
                if 'css-g5y9jx r-1xfd6ze r-18u37iz r-1w6e6rj r-1udh08x r-13qz1uu r-14lw9ot r-zmhlpu' in popped_class:
                    if self.current_team and self.current_team['name']:
                        self.teams.append(self.current_team)
                    self.current_team = None
                    self.in_team_container = False
                    self.in_playoff_section = False

                # End of playoff section
                elif 'css-g5y9jx r-obd0qt r-6koalj r-18u37iz' in popped_class:
                    self.in_playoff_section = False

            self.div_depth -= 1
            self.in_team_name = False
            self.in_record = False
            self.in_prob_label = False
            self.in_prob_value = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_team_name and self.current_team:
            # Team names are in all caps (e.g., "COLTS", "PATRIOTS")
            if data.isupper() and len(data) > 2 and not data.startswith('WEEK'):
                self.current_team['name'] = data

        elif self.in_record and self.current_team:
            # Record format: "7-1 • 1st AFC South"
            if '•' in data or '-' in data:
                # Extract just the W-L record
                parts = data.split('•')
                if parts:
                    record = parts[0].strip()
                    if '-' in record:
                        self.current_team['record'] = record

        elif self.in_prob_label:
            # Capture label (IF LOSE, CURRENT, IF WIN)
            if data in ['IF LOSE', 'CURRENT', 'IF WIN']:
                self.current_label = data

        elif self.in_prob_value and self.current_label and self.current_team:
            # Capture percentage value
            if '%' in data:
                value = data.replace('%', '').strip()

                # Handle "< 1" as 1.0
                if value.startswith('<'):
                    value = value.replace('<', '').strip()
                    if value == '' or value == '1':
                        value = '1'

                try:
                    value_float = float(value)

                    if self.current_label == 'CURRENT':
                        self.current_team['current_playoff_odds'] = value_float
                    elif self.current_label == 'IF WIN':
                        self.current_team['if_win_playoff_odds'] = value_float
                    elif self.current_label == 'IF LOSE':
                        self.current_team['if_lose_playoff_odds'] = value_float

                    self.current_label = None
                except ValueError:
                    pass


def parse_html_file(filepath):
    """Parse playoff odds from HTML file."""
    parser = PlayoffOddsParser()

    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
        parser.feed(html_content)

    return parser.teams


def extract_team_abbreviation(team_name):
    """Convert team name to 3-letter abbreviation."""
    name_map = {
        'CARDINALS': 'ARI',
        'FALCONS': 'ATL',
        'RAVENS': 'BAL',
        'BILLS': 'BUF',
        'PANTHERS': 'CAR',
        'BEARS': 'CHI',
        'BENGALS': 'CIN',
        'BROWNS': 'CLE',
        'COWBOYS': 'DAL',
        'BRONCOS': 'DEN',
        'LIONS': 'DET',
        'PACKERS': 'GB',
        'TEXANS': 'HOU',
        'COLTS': 'IND',
        'JAGUARS': 'JAX',
        'CHIEFS': 'KC',
        'RAIDERS': 'LV',
        'CHARGERS': 'LAC',
        'RAMS': 'LAR',
        'DOLPHINS': 'MIA',
        'VIKINGS': 'MIN',
        'PATRIOTS': 'NE',
        'SAINTS': 'NO',
        'GIANTS': 'NYG',
        'JETS': 'NYJ',
        'EAGLES': 'PHI',
        'STEELERS': 'PIT',
        '49ERS': 'SF',
        'SEAHAWKS': 'SEA',
        'BUCCANEERS': 'TB',
        'TITANS': 'TEN',
        'COMMANDERS': 'WSH',
    }
    return name_map.get(team_name, team_name)


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


def ensure_playoff_odds_columns(cursor):
    """Add playoff odds columns to standings table if they don't exist."""
    # Check if columns exist
    cursor.execute("PRAGMA table_info(standings)")
    columns = {row[1] for row in cursor.fetchall()}

    if 'if_win_playoff_odds' not in columns:
        print("Adding if_win_playoff_odds column to standings table...")
        cursor.execute("ALTER TABLE standings ADD COLUMN if_win_playoff_odds REAL")

    if 'if_lose_playoff_odds' not in columns:
        print("Adding if_lose_playoff_odds column to standings table...")
        cursor.execute("ALTER TABLE standings ADD COLUMN if_lose_playoff_odds REAL")


def save_to_database(teams, season, week):
    """Save playoff odds to database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Run init_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure columns exist
    ensure_playoff_odds_columns(cursor)
    conn.commit()

    print(f"\nUpdating playoff odds for Week {week}, {season}...")
    updated = 0
    errors = 0

    for team in teams:
        try:
            team_id = get_team_id(cursor, team['abbreviation'])

            # Update existing standings record
            cursor.execute("""
                UPDATE standings
                SET playoff_odds = ?,
                    if_win_playoff_odds = ?,
                    if_lose_playoff_odds = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE team_id = ? AND season = ? AND week = ?
            """, [
                team['current_playoff_odds'],
                team['if_win_playoff_odds'],
                team['if_lose_playoff_odds'],
                team_id, season, week
            ])

            if cursor.rowcount == 0:
                print(f"  ⚠️  No standings record found for {team['abbreviation']} (Week {week}, {season})")
                print(f"      Run scrape_standings.py first to create the base record.")
                errors += 1
            else:
                updated += 1

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            errors += 1
        except Exception as e:
            print(f"  ❌ Unexpected error for {team['abbreviation']}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"\n✅ Updated playoff odds for {updated} teams")
    if errors > 0:
        print(f"⚠️  {errors} teams had errors")

    return updated, errors


def main():
    parser = argparse.ArgumentParser(description='Parse playoff odds from NFL.com HTML')
    parser.add_argument('html_file', type=Path, help='Path to HTML file (e.g., playoff_odds.html)')
    parser.add_argument('--season', type=int, help='NFL season year (e.g., 2025)')
    parser.add_argument('--week', type=int, help='Week number')
    parser.add_argument('--output', type=Path, help='Output JSON file (optional)')
    parser.add_argument('--format', choices=['json', 'table', 'database'], default='table',
                       help='Output format (database requires --season and --week)')

    args = parser.parse_args()

    if not args.html_file.exists():
        print(f"❌ File not found: {args.html_file}")
        return 1

    # Validate database format requirements
    if args.format == 'database':
        if not args.season or not args.week:
            print("❌ --season and --week are required when using --format database")
            return 1

    print(f"Parsing playoff odds from {args.html_file}...")
    teams = parse_html_file(args.html_file)

    # Add abbreviations
    for team in teams:
        team['abbreviation'] = extract_team_abbreviation(team['name'])

    print(f"✓ Found playoff odds for {len(teams)} teams\n")

    if args.format == 'database':
        # Save to database
        updated, errors = save_to_database(teams, args.season, args.week)
        return 0 if errors == 0 else 1

    elif args.format == 'json':
        output_data = {
            'teams': teams,
            'source': 'NFL.com Playoff Picture',
            'count': len(teams)
        }

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✓ Saved to {args.output}")
        else:
            print(json.dumps(output_data, indent=2))

    else:  # table format
        # Sort by current playoff odds (descending)
        teams.sort(key=lambda x: x['current_playoff_odds'] or 0, reverse=True)

        print(f"{'Team':<6} {'Record':<8} {'Current':<8} {'If Lose':<8} {'If Win':<8}")
        print("-" * 50)

        for team in teams:
            abbr = team['abbreviation']
            record = team['record'] or 'N/A'
            current = f"{team['current_playoff_odds']:.0f}%" if team['current_playoff_odds'] is not None else 'N/A'
            if_lose = f"{team['if_lose_playoff_odds']:.0f}%" if team['if_lose_playoff_odds'] is not None else 'Bye'
            if_win = f"{team['if_win_playoff_odds']:.0f}%" if team['if_win_playoff_odds'] is not None else 'Bye'

            print(f"{abbr:<6} {record:<8} {current:<8} {if_lose:<8} {if_win:<8}")

    return 0


if __name__ == "__main__":
    exit(main())
