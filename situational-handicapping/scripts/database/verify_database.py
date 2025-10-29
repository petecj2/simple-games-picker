#!/usr/bin/env python3
"""
Verify database completeness and data quality.

Checks all tables and provides a summary of the database state.

Usage:
    python verify_database.py
"""

import sqlite3
import sys
from pathlib import Path

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"


def verify_database():
    """Verify database contents."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("NFL SITUATIONAL HANDICAPPING DATABASE VERIFICATION")
    print("=" * 60)

    # Check teams
    cursor.execute("SELECT COUNT(*) FROM teams")
    team_count = cursor.fetchone()[0]
    print(f"\n✓ TEAMS: {team_count}/32")

    if team_count < 32:
        print("  ⚠️  Warning: Missing teams!")
    else:
        cursor.execute("""
            SELECT conference, COUNT(*) as count
            FROM teams
            GROUP BY conference
        """)
        for conf, count in cursor.fetchall():
            print(f"    {conf}: {count} teams")

    # Check games
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    print(f"\n✓ GAMES: {total_games} total")

    cursor.execute("""
        SELECT season, week, COUNT(*) as count
        FROM games
        GROUP BY season, week
        ORDER BY season, week
    """)

    print("  By Week:")
    for season, week, count in cursor.fetchall():
        # Check travel calculations
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE season = ? AND week = ? AND travel_miles IS NOT NULL
        """, [season, week])
        with_travel = cursor.fetchone()[0]

        # Check completed games
        cursor.execute("""
            SELECT COUNT(*) FROM games
            WHERE season = ? AND week = ? AND home_score IS NOT NULL
        """, [season, week])
        completed = cursor.fetchone()[0]

        status = []
        if with_travel == count:
            status.append(f"{with_travel} w/travel")
        elif with_travel > 0:
            status.append(f"{with_travel}/{count} w/travel")

        if completed > 0:
            status.append(f"{completed} completed")

        status_str = ", ".join(status) if status else "scheduled"
        print(f"    {season} Week {week}: {count} games ({status_str})")

    # Check bye weeks
    cursor.execute("SELECT COUNT(*) FROM bye_weeks")
    bye_count = cursor.fetchone()[0]
    print(f"\n✓ BYE WEEKS: {bye_count} records")

    cursor.execute("""
        SELECT season, COUNT(*) as count
        FROM bye_weeks
        GROUP BY season
    """)

    for season, count in cursor.fetchall():
        print(f"    {season}: {count} teams")
        if count < 32:
            print(f"      ⚠️  Warning: Only {count}/32 teams have bye weeks")

    # Check standings
    cursor.execute("SELECT COUNT(*) FROM standings")
    standings_count = cursor.fetchone()[0]
    print(f"\n✓ STANDINGS: {standings_count} records")

    cursor.execute("""
        SELECT season, week, COUNT(*) as count
        FROM standings
        GROUP BY season, week
        ORDER BY season, week
    """)

    for season, week, count in cursor.fetchall():
        status = "✓" if count == 32 else f"⚠️  {count}/32"
        print(f"    {season} Week {week}: {status}")

    # Check situational trends
    cursor.execute("SELECT COUNT(*) FROM situational_trends")
    trends_count = cursor.fetchone()[0]
    print(f"\n✓ SITUATIONAL TRENDS: {trends_count} research-backed")

    cursor.execute("""
        SELECT situation_type, ats_percentage, confidence_level
        FROM situational_trends
        ORDER BY confidence_level DESC
    """)

    for situation, ats_pct, confidence in cursor.fetchall():
        print(f"    {situation}: {ats_pct}% ATS (confidence: {confidence}/10)")

    # Check primetime records
    cursor.execute("SELECT COUNT(*) FROM primetime_records")
    primetime_count = cursor.fetchone()[0]
    print(f"\n✓ PRIMETIME RECORDS: {primetime_count} records")

    # Check for situational factors in Week 9
    print("\n" + "=" * 60)
    print("WEEK 9 SITUATIONAL FACTORS")
    print("=" * 60)

    # Teams coming off bye in Week 9
    cursor.execute("""
        SELECT t.abbreviation, t.name
        FROM bye_weeks b
        JOIN teams t ON b.team_id = t.team_id
        WHERE b.season = 2025 AND b.bye_week_number = 9
        ORDER BY t.abbreviation
    """)

    bye_teams = cursor.fetchall()
    if bye_teams:
        print(f"\n✓ Teams ON BYE in Week 9: {len(bye_teams)}")
        for abbr, name in bye_teams:
            print(f"    {abbr} - {name}")

    # Teams playing in Week 10 after Week 9 bye
    cursor.execute("""
        SELECT t.abbreviation, t.name
        FROM bye_weeks b
        JOIN teams t ON b.team_id = t.team_id
        WHERE b.season = 2025 AND b.bye_week_number = 9
        ORDER BY t.abbreviation
    """)

    off_bye_week10 = cursor.fetchall()
    if off_bye_week10:
        print(f"\n✓ Teams COMING OFF BYE in Week 10: {len(off_bye_week10)}")
        print("  (Apply bye week advantage situational factor)")
        for abbr, name in off_bye_week10:
            print(f"    {abbr} - {name}")

    # Extreme travel games
    cursor.execute("""
        SELECT away.abbreviation, home.abbreviation, g.travel_miles, g.timezone_change
        FROM games g
        JOIN teams away ON g.away_team_id = away.team_id
        JOIN teams home ON g.home_team_id = home.team_id
        WHERE g.season = 2025 AND g.week = 9 AND g.travel_miles > 2000
        ORDER BY g.travel_miles DESC
    """)

    extreme_travel = cursor.fetchall()
    if extreme_travel:
        print(f"\n✓ EXTREME TRAVEL GAMES (>2000 miles): {len(extreme_travel)}")
        for away, home, miles, tz in extreme_travel:
            print(f"    {away} @ {home}: {miles:.1f} miles, {tz:+d} TZ")

    # Long travel with timezone changes
    cursor.execute("""
        SELECT away.abbreviation, home.abbreviation, g.travel_miles, g.timezone_change
        FROM games g
        JOIN teams away ON g.away_team_id = away.team_id
        JOIN teams home ON g.home_team_id = home.team_id
        WHERE g.season = 2025 AND g.week = 9
          AND g.travel_miles > 1500
          AND ABS(g.timezone_change) >= 2
        ORDER BY g.travel_miles DESC
    """)

    significant_travel = cursor.fetchall()
    if significant_travel:
        print(f"\n✓ SIGNIFICANT TRAVEL (>1500 miles + 2+ TZ): {len(significant_travel)}")
        for away, home, miles, tz in significant_travel:
            print(f"    {away} @ {home}: {miles:.1f} miles, {tz:+d} TZ")

    print("\n" + "=" * 60)
    print("✅ DATABASE VERIFICATION COMPLETE")
    print("=" * 60)

    # Summary
    issues = []
    if team_count < 32:
        issues.append("Missing teams")
    if total_games == 0:
        issues.append("No games loaded")

    if issues:
        print(f"\n⚠️  Issues found: {', '.join(issues)}")
    else:
        print("\n✅ Database ready for situational analysis!")

    conn.close()


if __name__ == "__main__":
    try:
        verify_database()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
