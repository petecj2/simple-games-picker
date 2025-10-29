#!/usr/bin/env python3
"""
Initialize the SQLite database for situational handicapping system.

Creates all necessary tables for tracking teams, games, bye weeks, standings,
situational trends, and primetime records.

Usage:
    python init_database.py
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "nfl_games.db"


def create_database():
    """Create the SQLite database with all necessary tables."""

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Creating database at: {DB_PATH}")

    # Create teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL UNIQUE,
            stadium_name TEXT,
            stadium_lat REAL,
            stadium_lon REAL,
            timezone TEXT,
            division TEXT,
            conference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created teams table")

    # Create games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            game_date DATE NOT NULL,
            game_time TIME,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            venue TEXT,
            travel_miles REAL,
            timezone_change INTEGER,
            is_primetime BOOLEAN DEFAULT 0,
            is_divisional BOOLEAN DEFAULT 0,
            is_revenge BOOLEAN DEFAULT 0,
            home_score INTEGER,
            away_score INTEGER,
            home_spread REAL,
            away_spread REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (home_team_id) REFERENCES teams (team_id),
            FOREIGN KEY (away_team_id) REFERENCES teams (team_id),
            UNIQUE(season, week, home_team_id, away_team_id)
        )
    """)
    print("✓ Created games table")

    # Create bye_weeks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bye_weeks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            bye_week_number INTEGER NOT NULL,
            historical_ats_record TEXT,
            historical_sample_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id),
            UNIQUE(team_id, season)
        )
    """)
    print("✓ Created bye_weeks table")

    # Create standings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            ties INTEGER DEFAULT 0,
            division_rank INTEGER,
            conference_rank INTEGER,
            playoff_odds REAL,
            games_behind REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id),
            UNIQUE(team_id, season, week)
        )
    """)
    print("✓ Created standings table")

    # Create situational_trends table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS situational_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            situation_type TEXT NOT NULL,
            description TEXT,
            ats_wins INTEGER,
            ats_losses INTEGER,
            ats_pushes INTEGER,
            ats_percentage REAL,
            sample_size INTEGER,
            confidence_level INTEGER,
            source TEXT,
            date_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(situation_type)
        )
    """)
    print("✓ Created situational_trends table")

    # Create primetime_records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS primetime_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            game_type TEXT NOT NULL,
            su_wins INTEGER DEFAULT 0,
            su_losses INTEGER DEFAULT 0,
            ats_wins INTEGER DEFAULT 0,
            ats_losses INTEGER DEFAULT 0,
            ats_pushes INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id),
            UNIQUE(team_id, season, game_type)
        )
    """)
    print("✓ Created primetime_records table")

    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_week ON games(season, week)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_standings_week ON standings(season, week)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bye_weeks_season ON bye_weeks(season)")
    print("✓ Created indexes")

    # Insert research-backed situational trends
    situational_trends = [
        (
            'BYE_WEEK_ADVANTAGE',
            'Road favorites vs divisional opponents after bye week',
            32, 16, 0, 66.7, 48, 8,
            'VSiN Research',
            '2002-present'
        ),
        (
            'HOME_AFTER_BYE_NON_CONF',
            'Playing against home teams coming off bye (non-conference)',
            25, 13, 2, 65.8, 40, 7,
            'VSiN Research',
            '2015-present'
        ),
        (
            'MNF_DIVISIONAL_AFTER_BYE',
            'Monday Night divisional games vs bye week teams',
            26, 15, 1, 63.4, 42, 7,
            'VSiN Research',
            '1992-present'
        ),
        (
            'DOUBLE_DIGIT_FAV_AFTER_BYE',
            'Double-digit favorites coming off bye week',
            18, 8, 1, 69.2, 27, 8,
            'VSiN Research',
            '2014-present'
        ),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO situational_trends
        (situation_type, description, ats_wins, ats_losses, ats_pushes,
         ats_percentage, sample_size, confidence_level, source, date_range)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, situational_trends)
    print(f"✓ Inserted {len(situational_trends)} research-backed situational trends")

    # Commit changes
    conn.commit()
    print("\n✅ Database initialization complete!")
    print(f"   Location: {DB_PATH}")
    print(f"   Tables: teams, games, bye_weeks, standings, situational_trends, primetime_records")

    # Display table counts
    cursor.execute("SELECT COUNT(*) FROM teams")
    print(f"   Teams: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM situational_trends")
    print(f"   Situational trends: {cursor.fetchone()[0]}")

    conn.close()


def verify_database():
    """Verify the database was created correctly."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check all tables exist
    tables = ['teams', 'games', 'bye_weeks', 'standings', 'situational_trends', 'primetime_records']
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    all_exist = all(table in existing_tables for table in tables)

    if all_exist:
        print("\n✅ Database verification passed")
    else:
        missing = set(tables) - existing_tables
        print(f"\n❌ Missing tables: {missing}")

    conn.close()
    return all_exist


if __name__ == "__main__":
    try:
        create_database()
        verify_database()
    except Exception as e:
        print(f"\n❌ Error creating database: {e}", file=sys.stderr)
        sys.exit(1)
