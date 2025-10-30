#!/usr/bin/env python3
"""
Update Week 9 standings from Pro Football Reference data.

Updates the standings table with actual 2025 NFL records through Week 8.

Usage:
    python update_week9_standings.py
"""

import sqlite3
import sys
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR.parent.parent / "data" / "nfl_games.db"

# Standings data from Pro Football Reference (through Week 8, 2025)
STANDINGS_DATA = {
    # AFC East
    'NE': (6, 2, 0),
    'BUF': (5, 2, 0),
    'MIA': (2, 6, 0),
    'NYJ': (1, 7, 0),

    # AFC North
    'PIT': (4, 3, 0),
    'CIN': (3, 5, 0),
    'BAL': (2, 5, 0),
    'CLE': (2, 6, 0),

    # AFC South
    'IND': (7, 1, 0),
    'JAX': (4, 3, 0),
    'HOU': (3, 4, 0),
    'TEN': (1, 7, 0),

    # AFC West
    'DEN': (6, 2, 0),
    'KC': (5, 3, 0),
    'LAC': (5, 3, 0),
    'LV': (2, 5, 0),

    # NFC East
    'PHI': (6, 2, 0),
    'DAL': (3, 4, 1),
    'WSH': (3, 5, 0),
    'NYG': (2, 6, 0),

    # NFC North
    'GB': (5, 1, 1),
    'DET': (5, 2, 0),
    'CHI': (4, 3, 0),
    'MIN': (3, 4, 0),

    # NFC South
    'TB': (6, 2, 0),
    'CAR': (4, 4, 0),
    'ATL': (3, 4, 0),
    'NO': (1, 7, 0),

    # NFC West
    'LAR': (5, 2, 0),
    'SEA': (5, 2, 0),
    'SF': (5, 3, 0),
    'ARI': (2, 5, 0),
}


def calculate_playoff_odds(wins, losses, ties, total_games=17):
    """
    Estimate playoff odds based on current record.

    Simple heuristic based on historical playoff cutoff (~9-10 wins):
    - Teams need roughly 9-10 wins to make playoffs
    - Calculate probability based on current pace and games remaining
    """
    games_played = wins + losses + ties
    games_remaining = total_games - games_played

    if games_remaining == 0:
        # Season over, either in (100%) or out (0%)
        return 100.0 if wins >= 9 else 0.0

    # Current win percentage
    win_pct = (wins + ties * 0.5) / games_played if games_played > 0 else 0.5

    # Projected final wins
    projected_wins = wins + (win_pct * games_remaining)

    # Playoff odds based on projected wins
    # ~50% at 9 wins, scaling up/down from there
    if projected_wins >= 11:
        return min(95.0, 50.0 + (projected_wins - 9) * 20)
    elif projected_wins >= 9:
        return 50.0 + (projected_wins - 9) * 20
    elif projected_wins >= 7:
        return 20.0 + (projected_wins - 7) * 15
    else:
        return max(1.0, projected_wins * 3)


def update_standings():
    """Update standings table with Week 9 data."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if standings exist for Week 9
    cursor.execute("SELECT COUNT(*) FROM standings WHERE season = 2025 AND week = 9")
    existing = cursor.fetchone()[0]

    if existing > 0:
        print(f"⚠️  Warning: {existing} standings entries already exist for Week 9")
        cursor.execute("DELETE FROM standings WHERE season = 2025 AND week = 9")
        print(f"✓ Deleted {existing} existing standings")

    print("\nUpdating Week 9 standings...")
    inserted = 0

    for abbr, (wins, losses, ties) in STANDINGS_DATA.items():
        # Get team_id
        cursor.execute("SELECT team_id FROM teams WHERE abbreviation = ?", [abbr])
        result = cursor.fetchone()

        if not result:
            print(f"  ❌ Team not found: {abbr}")
            continue

        team_id = result[0]

        # Calculate playoff odds
        playoff_odds = calculate_playoff_odds(wins, losses, ties)

        # Insert standing
        cursor.execute("""
            INSERT INTO standings (season, week, team_id, wins, losses, ties, playoff_odds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [2025, 9, team_id, wins, losses, ties, playoff_odds])

        inserted += 1
        print(f"  ✓ {abbr}: {wins}-{losses}-{ties} ({playoff_odds:.1f}% playoff odds)")

    conn.commit()
    print(f"\n✅ Successfully updated {inserted} team standings for Week 9")

    # Show playoff race
    print("\n📊 Playoff Race (sorted by odds):")
    cursor.execute("""
        SELECT t.abbreviation, s.wins, s.losses, s.ties, s.playoff_odds
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        WHERE s.season = 2025 AND s.week = 9
        ORDER BY s.playoff_odds DESC
        LIMIT 15
    """)

    print("\nTop 15 Playoff Contenders:")
    for abbr, w, l, t, odds in cursor.fetchall():
        record = f"{w}-{l}" if t == 0 else f"{w}-{l}-{t}"
        print(f"  {abbr:3s}: {record:7s} - {odds:5.1f}%")

    conn.close()


if __name__ == "__main__":
    try:
        update_standings()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
