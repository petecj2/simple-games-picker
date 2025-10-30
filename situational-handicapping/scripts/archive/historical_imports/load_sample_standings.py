#!/usr/bin/env python3
"""
Load sample standings for testing situational handicapping calculations.

Creates realistic Week 9 standings based on typical NFL patterns.

Usage:
    python load_sample_standings.py
"""

import sqlite3
import sys
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"


def get_team_id(cursor, abbr):
    """Get team_id for a team abbreviation."""
    cursor.execute("SELECT team_id, name FROM teams WHERE abbreviation = ?", [abbr])
    result = cursor.fetchone()
    if result:
        return result[0], result[1]
    raise ValueError(f"Team not found: {abbr}")


def load_sample_standings():
    """Load sample standings for Week 9, 2025."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    season = 2025
    week = 9

    # Sample standings (W, L, Div Rank, Conf Rank, Playoff %, GB)
    # Format: abbreviation: (wins, losses, ties, div_rank, conf_rank, playoff_odds, games_behind)
    standings_data = {
        # AFC East
        'BUF': (6, 2, 0, 1, 3, 85.0, 0.0),
        'MIA': (5, 3, 0, 2, 8, 65.0, 1.0),
        'NYJ': (3, 5, 0, 3, 12, 15.0, 3.0),
        'NE': (2, 6, 0, 4, 15, 5.0, 4.0),

        # AFC North
        'BAL': (6, 2, 0, 1, 2, 90.0, 0.0),
        'PIT': (6, 2, 0, 2, 4, 88.0, 0.0),
        'CIN': (4, 4, 0, 3, 10, 45.0, 2.0),
        'CLE': (2, 6, 0, 4, 14, 8.0, 4.0),

        # AFC South
        'HOU': (6, 2, 0, 1, 5, 82.0, 0.0),
        'IND': (4, 4, 0, 2, 9, 48.0, 2.0),
        'JAX': (3, 5, 0, 3, 13, 18.0, 3.0),
        'TEN': (2, 6, 0, 4, 16, 6.0, 4.0),

        # AFC West
        'KC': (7, 1, 0, 1, 1, 98.0, 0.0),
        'LAC': (5, 3, 0, 2, 7, 68.0, 2.0),
        'DEN': (4, 4, 0, 3, 11, 42.0, 3.0),
        'LV': (2, 6, 0, 4, 17, 4.0, 5.0),

        # NFC East
        'WSH': (6, 2, 0, 1, 4, 86.0, 0.0),
        'PHI': (5, 3, 0, 2, 6, 72.0, 1.0),
        'DAL': (3, 5, 0, 3, 12, 22.0, 3.0),
        'NYG': (2, 6, 0, 4, 15, 7.0, 4.0),

        # NFC North
        'DET': (7, 1, 0, 1, 1, 96.0, 0.0),
        'GB': (6, 2, 0, 2, 3, 89.0, 1.0),
        'MIN': (5, 3, 0, 3, 7, 70.0, 2.0),
        'CHI': (4, 4, 0, 4, 10, 38.0, 3.0),

        # NFC South
        'ATL': (5, 3, 0, 1, 8, 66.0, 0.0),
        'TB': (4, 4, 0, 2, 11, 44.0, 1.0),
        'NO': (3, 5, 0, 3, 13, 19.0, 2.0),
        'CAR': (2, 6, 0, 4, 16, 5.0, 3.0),

        # NFC West
        'SF': (5, 3, 0, 1, 5, 78.0, 0.0),
        'SEA': (4, 4, 0, 2, 9, 52.0, 1.0),
        'ARI': (4, 4, 0, 3, 14, 36.0, 1.0),
        'LAR': (3, 5, 0, 4, 14, 16.0, 2.0),
    }

    # Check if standings already exist
    cursor.execute("SELECT COUNT(*) FROM standings WHERE season = ? AND week = ?", [season, week])
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} standings records already exist for Week {week}, {season}")
        print("Deleting existing records...")
        cursor.execute("DELETE FROM standings WHERE season = ? AND week = ?", [season, week])
        print(f"✓ Deleted {existing} existing standings records")

    print(f"\nLoading Week {week}, {season} standings...")
    inserted = 0

    for team_abbr, (wins, losses, ties, div_rank, conf_rank, playoff_odds, gb) in standings_data.items():
        try:
            team_id, team_name = get_team_id(cursor, team_abbr)

            cursor.execute("""
                INSERT INTO standings (team_id, season, week, wins, losses, ties,
                                     division_rank, conference_rank, playoff_odds, games_behind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [team_id, season, week, wins, losses, ties, div_rank, conf_rank, playoff_odds, gb])

            inserted += 1
            record = f"{wins}-{losses}" + (f"-{ties}" if ties > 0 else "")
            print(f"  ✓ {team_abbr}: {record} (Div: {div_rank}, Conf: {conf_rank}, Playoff: {playoff_odds}%)")

        except ValueError as e:
            print(f"  ❌ Error: {e}")
            continue

    conn.commit()

    print(f"\n✅ Loaded standings for {inserted} teams")

    # Show playoff race summary
    print(f"\nWeek {week} Playoff Picture:")

    for conf in ['AFC', 'NFC']:
        cursor.execute("""
            SELECT t.abbreviation, s.wins, s.losses, s.playoff_odds, s.conference_rank
            FROM standings s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.season = ? AND s.week = ? AND t.conference = ?
            ORDER BY s.conference_rank
            LIMIT 7
        """, [season, week, conf])

        print(f"\n{conf} (Top 7):")
        for abbr, wins, losses, playoff_odds, rank in cursor.fetchall():
            status = "✓" if rank <= 7 else " "
            print(f"  {status} {rank}. {abbr}: {wins}-{losses} ({playoff_odds}% playoff odds)")

    conn.close()


if __name__ == "__main__":
    try:
        load_sample_standings()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
