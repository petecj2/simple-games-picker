#!/usr/bin/env python3
"""
Calculate travel distances and timezone changes for NFL games.

Uses the haversine formula to calculate great circle distance between
stadium coordinates. Updates the games database with travel_miles and
timezone_change columns.

Usage:
    python calculate_travel.py --season 2025
    python calculate_travel.py --season 2025 --week 9
"""

import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import pytz

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
DB_PATH = DATA_DIR / "nfl_games.db"
COORDS_PATH = DATA_DIR / "stadium_coordinates.json"


def load_stadium_coordinates():
    """Load stadium coordinates from JSON file."""
    if not COORDS_PATH.exists():
        raise FileNotFoundError(f"Stadium coordinates file not found: {COORDS_PATH}")

    with open(COORDS_PATH, 'r') as f:
        data = json.load(f)

    return data['teams']


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)

    Returns:
        Distance in miles
    """
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of Earth in miles
    radius_miles = 3959.0

    distance = radius_miles * c
    return round(distance, 1)


def get_timezone_offset(tz1_str, tz2_str):
    """
    Calculate timezone offset between two timezones.

    Args:
        tz1_str: Timezone string (e.g., 'America/New_York')
        tz2_str: Timezone string (e.g., 'America/Los_Angeles')

    Returns:
        Integer representing hour difference (can be negative)
    """
    try:
        tz1 = pytz.timezone(tz1_str)
        tz2 = pytz.timezone(tz2_str)

        # Use a representative date (during NFL season, not DST transition)
        representative_date = datetime(2025, 10, 15, 12, 0, 0)

        dt1 = tz1.localize(representative_date)
        dt2 = tz2.localize(representative_date)

        # Calculate difference in hours
        offset_seconds = (dt2.utcoffset().total_seconds() - dt1.utcoffset().total_seconds())
        offset_hours = int(offset_seconds / 3600)

        return offset_hours
    except Exception as e:
        print(f"Warning: Could not calculate timezone offset: {e}")
        return 0


def calculate_travel_for_games(season, week=None):
    """
    Calculate travel distance and timezone changes for games.

    Args:
        season: NFL season year (e.g., 2025)
        week: Specific week number, or None for all weeks
    """
    # Load stadium coordinates
    teams = load_stadium_coordinates()

    # Connect to database
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}\nRun init_database.py first.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Build query
    query = """
        SELECT g.game_id, away.abbreviation as away_abbr, home.abbreviation as home_abbr
        FROM games g
        JOIN teams away ON g.away_team_id = away.team_id
        JOIN teams home ON g.home_team_id = home.team_id
        WHERE g.season = ?
    """
    params = [season]

    if week is not None:
        query += " AND g.week = ?"
        params.append(week)

    cursor.execute(query, params)
    games = cursor.fetchall()

    if not games:
        print(f"No games found for season {season}" + (f" week {week}" if week else ""))
        conn.close()
        return

    print(f"Calculating travel for {len(games)} games...")

    updates = []
    for game_id, away_abbr, home_abbr in games:
        # Get team data
        away_team = teams.get(away_abbr)
        home_team = teams.get(home_abbr)

        if not away_team or not home_team:
            print(f"Warning: Missing data for {away_abbr} @ {home_abbr}")
            continue

        # Calculate distance (away team travels to home stadium)
        distance = haversine_distance(
            away_team['latitude'], away_team['longitude'],
            home_team['latitude'], home_team['longitude']
        )

        # Calculate timezone change (negative means traveling east, positive west)
        tz_change = get_timezone_offset(away_team['timezone'], home_team['timezone'])

        updates.append((distance, tz_change, game_id))

        print(f"  {away_abbr} @ {home_abbr}: {distance} miles, {tz_change:+d} timezone")

    # Update database
    cursor.executemany("""
        UPDATE games
        SET travel_miles = ?, timezone_change = ?, updated_at = CURRENT_TIMESTAMP
        WHERE game_id = ?
    """, updates)

    conn.commit()
    print(f"\n✅ Updated {len(updates)} games with travel data")

    # Show summary statistics
    cursor.execute("""
        SELECT AVG(travel_miles), MAX(travel_miles), MIN(travel_miles)
        FROM games
        WHERE season = ? AND travel_miles IS NOT NULL
    """, [season])

    avg, max_dist, min_dist = cursor.fetchone()
    print(f"\nTravel Statistics:")
    print(f"  Average: {avg:.1f} miles")
    print(f"  Maximum: {max_dist:.1f} miles")
    print(f"  Minimum: {min_dist:.1f} miles")

    # Show games with extreme travel
    cursor.execute("""
        SELECT away.abbreviation, home.abbreviation, g.travel_miles, g.timezone_change, g.week
        FROM games g
        JOIN teams away ON g.away_team_id = away.team_id
        JOIN teams home ON g.home_team_id = home.team_id
        WHERE g.season = ? AND g.travel_miles > 2000
        ORDER BY g.travel_miles DESC
        LIMIT 10
    """, [season])

    extreme_travel = cursor.fetchall()
    if extreme_travel:
        print(f"\nGames with extreme travel (>2000 miles):")
        for away, home, miles, tz, wk in extreme_travel:
            print(f"  Week {wk}: {away} @ {home} - {miles} miles, {tz:+d} TZ")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Calculate travel distances for NFL games')
    parser.add_argument('--season', type=int, required=True, help='NFL season year (e.g., 2025)')
    parser.add_argument('--week', type=int, help='Specific week number (optional)')

    args = parser.parse_args()

    try:
        calculate_travel_for_games(args.season, args.week)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
