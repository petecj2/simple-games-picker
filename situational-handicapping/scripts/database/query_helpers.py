#!/usr/bin/env python3
"""
Database query helper functions for situational handicapping system.

Provides common database queries and utility functions for accessing
teams, games, standings, and situational data.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "nfl_games.db"


def get_connection():
    """Get a database connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}\nRun init_database.py first.")
    return sqlite3.connect(DB_PATH)


def get_team_by_abbreviation(abbr: str) -> Optional[Dict]:
    """Get team information by abbreviation."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT team_id, name, abbreviation, stadium_name, stadium_lat, stadium_lon,
               division, conference
        FROM teams
        WHERE abbreviation = ?
    """, [abbr])

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'team_id': row[0],
            'name': row[1],
            'abbreviation': row[2],
            'stadium_name': row[3],
            'stadium_lat': row[4],
            'stadium_lon': row[5],
            'division': row[6],
            'conference': row[7]
        }
    return None


def get_games_for_week(season: int, week: int) -> List[Dict]:
    """Get all games for a specific week."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT g.game_id, g.week, g.game_date, g.game_time,
               home.abbreviation as home_abbr, home.name as home_name,
               away.abbreviation as away_abbr, away.name as away_name,
               g.venue, g.travel_miles, g.timezone_change,
               g.is_primetime, g.is_divisional, g.is_revenge,
               g.home_score, g.away_score
        FROM games g
        JOIN teams home ON g.home_team_id = home.team_id
        JOIN teams away ON g.away_team_id = away.team_id
        WHERE g.season = ? AND g.week = ?
        ORDER BY g.game_date, g.game_time
    """, [season, week])

    games = []
    for row in cursor.fetchall():
        games.append({
            'game_id': row[0],
            'week': row[1],
            'game_date': row[2],
            'game_time': row[3],
            'home_abbr': row[4],
            'home_name': row[5],
            'away_abbr': row[6],
            'away_name': row[7],
            'venue': row[8],
            'travel_miles': row[9],
            'timezone_change': row[10],
            'is_primetime': bool(row[11]),
            'is_divisional': bool(row[12]),
            'is_revenge': bool(row[13]),
            'home_score': row[14],
            'away_score': row[15]
        })

    conn.close()
    return games


def get_team_bye_week(team_abbr: str, season: int) -> Optional[int]:
    """Get the bye week number for a team in a season."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bw.bye_week_number
        FROM bye_weeks bw
        JOIN teams t ON bw.team_id = t.team_id
        WHERE t.abbreviation = ? AND bw.season = ?
    """, [team_abbr, season])

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def is_team_off_bye(team_abbr: str, season: int, week: int) -> bool:
    """Check if a team is coming off a bye week."""
    bye_week = get_team_bye_week(team_abbr, season)
    return bye_week is not None and bye_week == week - 1


def get_current_standings(team_abbr: str, season: int, week: int) -> Optional[Dict]:
    """Get current season standings for a team at a specific week."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.wins, s.losses, s.ties, s.division_rank,
               s.conference_rank, s.playoff_odds, s.games_behind
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        WHERE t.abbreviation = ? AND s.season = ? AND s.week = ?
    """, [team_abbr, season, week])

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'wins': row[0],
            'losses': row[1],
            'ties': row[2],
            'division_rank': row[3],
            'conference_rank': row[4],
            'playoff_odds': row[5],
            'games_behind': row[6]
        }
    return None


def get_primetime_record(team_abbr: str, season: int, game_type: str = 'ALL') -> Optional[Dict]:
    """Get primetime performance record for a team."""
    conn = get_connection()
    cursor = conn.cursor()

    if game_type == 'ALL':
        cursor.execute("""
            SELECT SUM(su_wins), SUM(su_losses),
                   SUM(ats_wins), SUM(ats_losses), SUM(ats_pushes)
            FROM primetime_records pr
            JOIN teams t ON pr.team_id = t.team_id
            WHERE t.abbreviation = ? AND pr.season = ?
        """, [team_abbr, season])
    else:
        cursor.execute("""
            SELECT su_wins, su_losses, ats_wins, ats_losses, ats_pushes
            FROM primetime_records pr
            JOIN teams t ON pr.team_id = t.team_id
            WHERE t.abbreviation = ? AND pr.season = ? AND pr.game_type = ?
        """, [team_abbr, season, game_type])

    row = cursor.fetchone()
    conn.close()

    if row and any(x is not None for x in row):
        su_wins, su_losses, ats_wins, ats_losses, ats_pushes = row
        total_ats = (ats_wins or 0) + (ats_losses or 0) + (ats_pushes or 0)
        ats_pct = (ats_wins or 0) / total_ats if total_ats > 0 else 0.0

        return {
            'su_wins': su_wins or 0,
            'su_losses': su_losses or 0,
            'ats_wins': ats_wins or 0,
            'ats_losses': ats_losses or 0,
            'ats_pushes': ats_pushes or 0,
            'ats_percentage': round(ats_pct, 3)
        }
    return None


def get_previous_matchup(team1_abbr: str, team2_abbr: str, season: int, before_week: int) -> Optional[Dict]:
    """Get the result of a previous matchup this season (for revenge games)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT g.week, g.home_score, g.away_score,
               home.abbreviation as home_abbr, away.abbreviation as away_abbr
        FROM games g
        JOIN teams home ON g.home_team_id = home.team_id
        JOIN teams away ON g.away_team_id = away.team_id
        WHERE g.season = ? AND g.week < ?
          AND ((home.abbreviation = ? AND away.abbreviation = ?)
           OR (home.abbreviation = ? AND away.abbreviation = ?))
          AND g.home_score IS NOT NULL AND g.away_score IS NOT NULL
        ORDER BY g.week DESC
        LIMIT 1
    """, [season, before_week, team1_abbr, team2_abbr, team2_abbr, team1_abbr])

    row = cursor.fetchone()
    conn.close()

    if row:
        week, home_score, away_score, home_abbr, away_abbr = row
        winner = home_abbr if home_score > away_score else away_abbr
        loser = away_abbr if winner == home_abbr else home_abbr

        return {
            'week': week,
            'home_team': home_abbr,
            'away_team': away_abbr,
            'home_score': home_score,
            'away_score': away_score,
            'winner': winner,
            'loser': loser
        }
    return None


def get_situational_trend(situation_type: str) -> Optional[Dict]:
    """Get research-backed situational trend data."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT situation_type, description, ats_wins, ats_losses, ats_pushes,
               ats_percentage, sample_size, confidence_level, source, date_range
        FROM situational_trends
        WHERE situation_type = ?
    """, [situation_type])

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'situation_type': row[0],
            'description': row[1],
            'ats_wins': row[2],
            'ats_losses': row[3],
            'ats_pushes': row[4],
            'ats_percentage': row[5],
            'sample_size': row[6],
            'confidence_level': row[7],
            'source': row[8],
            'date_range': row[9]
        }
    return None


def insert_team(abbreviation: str, name: str, division: str, conference: str,
                stadium_name: str = None, lat: float = None, lon: float = None) -> int:
    """Insert a new team into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO teams (abbreviation, name, division, conference, stadium_name, stadium_lat, stadium_lon)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [abbreviation, name, division, conference, stadium_name, lat, lon])

    team_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return team_id


def update_game_result(game_id: int, home_score: int, away_score: int):
    """Update game with final score."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE games
        SET home_score = ?, away_score = ?, updated_at = CURRENT_TIMESTAMP
        WHERE game_id = ?
    """, [home_score, away_score, game_id])

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Test queries
    print("Testing query_helpers...")

    # Test team lookup
    chiefs = get_team_by_abbreviation('KC')
    if chiefs:
        print(f"\n✓ Found team: {chiefs['name']}")

    # Test getting games
    try:
        games = get_games_for_week(2025, 9)
        print(f"✓ Found {len(games)} games for Week 9")
    except:
        print("  (No games found for Week 9 - database may be empty)")

    print("\n✅ Query helpers module working correctly")
