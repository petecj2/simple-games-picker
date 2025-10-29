#!/usr/bin/env python3
"""
Calculate situational scores for NFL games.

Applies situational weights to games based on bye weeks, travel, motivation,
and other context factors. Outputs scores for each team showing situational edges.

Usage:
    python calculate_situational_score.py --season 2025 --week 9
    python calculate_situational_score.py --season 2025 --week 9 --verbose
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Path configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
CONFIG_DIR = SCRIPT_DIR.parent.parent / "config"
DB_PATH = DATA_DIR / "nfl_games.db"
WEIGHTS_PATH = CONFIG_DIR / "situational_weights.json"
THRESHOLDS_PATH = CONFIG_DIR / "research_thresholds.json"


def load_config():
    """Load configuration files."""
    with open(WEIGHTS_PATH, 'r') as f:
        weights = json.load(f)

    with open(THRESHOLDS_PATH, 'r') as f:
        thresholds = json.load(f)

    return weights, thresholds


def get_team_info(cursor, team_id):
    """Get team information."""
    cursor.execute("""
        SELECT abbreviation, name, conference, division, timezone
        FROM teams
        WHERE team_id = ?
    """, [team_id])
    row = cursor.fetchone()
    if row:
        return {
            'abbr': row[0],
            'name': row[1],
            'conference': row[2],
            'division': row[3],
            'timezone': row[4]
        }
    return None


def is_west_coast_team(timezone):
    """Check if team is in Pacific timezone."""
    return timezone in ['America/Los_Angeles', 'America/Phoenix']


def is_east_coast_team(timezone):
    """Check if team is in Eastern timezone."""
    return timezone == 'America/New_York'


def check_bye_week_advantage(cursor, team_abbr, opponent_abbr, season, week, is_road, weights):
    """
    Check for bye week advantage.

    Road favorites after bye vs divisional opponents: +3.0 points
    """
    config = weights['bye_week_advantage']

    # Check if team is coming off bye
    cursor.execute("""
        SELECT bye_week_number FROM bye_weeks b
        JOIN teams t ON b.team_id = t.team_id
        WHERE t.abbreviation = ? AND b.season = ?
    """, [team_abbr, season])

    bye_result = cursor.fetchone()
    if not bye_result:
        return 0.0, None

    bye_week = bye_result[0]

    # Team must be coming off bye (played last week = bye week)
    if bye_week != week - 1:
        return 0.0, None

    # Check if opponent is divisional
    cursor.execute("""
        SELECT t1.division, t2.division
        FROM teams t1, teams t2
        WHERE t1.abbreviation = ? AND t2.abbreviation = ?
    """, [team_abbr, opponent_abbr])

    div_result = cursor.fetchone()
    if not div_result:
        return 0.0, None

    team_div, opp_div = div_result
    is_divisional = (team_div == opp_div)

    # Must be road team and divisional opponent
    if is_road and is_divisional:
        return config['points'], f"Road favorite off bye vs divisional opponent ({config['research_ats']})"

    return 0.0, None


def check_home_after_bye_nonconf(cursor, team_abbr, opponent_abbr, season, week, is_home, weights):
    """
    Check for home after bye non-conference fade.

    Home teams off bye vs non-conference: -2.5 points (fade home team)
    """
    config = weights['home_after_bye_nonconference']

    if not is_home:
        return 0.0, None

    # Check if team is coming off bye
    cursor.execute("""
        SELECT bye_week_number FROM bye_weeks b
        JOIN teams t ON b.team_id = t.team_id
        WHERE t.abbreviation = ? AND b.season = ?
    """, [team_abbr, season])

    bye_result = cursor.fetchone()
    if not bye_result:
        return 0.0, None

    bye_week = bye_result[0]

    if bye_week != week - 1:
        return 0.0, None

    # Check if opponent is non-conference
    cursor.execute("""
        SELECT t1.conference, t2.conference
        FROM teams t1, teams t2
        WHERE t1.abbreviation = ? AND t2.abbreviation = ?
    """, [team_abbr, opponent_abbr])

    conf_result = cursor.fetchone()
    if not conf_result:
        return 0.0, None

    team_conf, opp_conf = conf_result
    is_nonconference = (team_conf != opp_conf)

    if is_nonconference:
        return config['points'], f"Home team off bye vs non-conference ({config['research_ats']})"

    return 0.0, None


def check_extreme_travel(travel_miles, timezone_change, weights):
    """
    Check for extreme travel impact.

    >2000 miles + 3 timezone change: -2.0 points
    """
    config = weights['extreme_travel']

    if travel_miles > config['miles_threshold'] and abs(timezone_change) >= config['timezone_threshold']:
        return config['points'], f"Extreme travel: {travel_miles:.0f} miles, {timezone_change:+d} TZ"

    return 0.0, None


def check_morning_body_clock(cursor, away_team_info, home_team_info, game_time, timezone_change, weights):
    """
    Check for morning body clock disadvantage.

    West Coast team at 10am local time on East Coast: -3.0 points
    """
    config = weights['morning_body_clock']

    # Must be West Coast team traveling to East Coast
    if not is_west_coast_team(away_team_info['timezone']):
        return 0.0, None

    if not is_east_coast_team(home_team_info['timezone']):
        return 0.0, None

    # Check game time (must be early afternoon ET)
    if game_time:
        try:
            hour = int(game_time.split(':')[0])
            # 1pm ET kickoff = 10am PT (morning body clock)
            if 13 <= hour <= 14:  # 1-2pm ET
                return config['points'], f"Morning body clock: West Coast at 10am local time"
        except:
            pass

    return 0.0, None


def check_primetime_edge(cursor, team_abbr, home_team_info, game_time, weights):
    """
    Check for primetime edge.

    West Coast team in primetime (8pm+ ET) traveling east: +1.5 points
    """
    config = weights['primetime_edge']

    # Check if game is primetime (8pm ET or later)
    is_primetime = False
    if game_time:
        try:
            hour = int(game_time.split(':')[0])
            if hour >= 20:  # 8pm or later
                is_primetime = True
        except:
            pass

    if not is_primetime:
        return 0.0, None

    # Get team info
    cursor.execute("""
        SELECT timezone FROM teams WHERE abbreviation = ?
    """, [team_abbr])

    result = cursor.fetchone()
    if not result:
        return 0.0, None

    team_tz = result[0]

    # Must be West Coast team
    if not is_west_coast_team(team_tz):
        return 0.0, None

    # Must be traveling to East Coast
    if is_east_coast_team(home_team_info['timezone']):
        return config['points'], f"Primetime edge: West Coast team in primetime ({config['research_ats']})"

    return 0.0, None


def check_short_week(cursor, game_date, weights):
    """
    Check for Thursday Night Football short week.

    TNF impact varies by week.
    """
    config = weights['short_week_disadvantage']

    # Check if Thursday game
    try:
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')
        if game_dt.weekday() == 3:  # Thursday = 3
            return config['points'], "Thursday Night Football short week"
    except:
        pass

    return 0.0, None


def check_playoff_desperation(cursor, team_abbr, opponent_abbr, season, week, weights):
    """
    Check for playoff desperation factor.

    Playoff-bound team vs eliminated opponent (Week 15+): +2.0 points
    """
    config = weights['playoff_desperation']

    # Only applies Week 15+
    if week < config['week_threshold']:
        return 0.0, None

    # Get standings
    cursor.execute("""
        SELECT s.playoff_odds
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        WHERE t.abbreviation = ? AND s.season = ? AND s.week = ?
    """, [team_abbr, season, week])

    team_result = cursor.fetchone()

    cursor.execute("""
        SELECT s.playoff_odds
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        WHERE t.abbreviation = ? AND s.season = ? AND s.week = ?
    """, [opponent_abbr, season, week])

    opp_result = cursor.fetchone()

    if not team_result or not opp_result:
        return 0.0, None

    team_odds = team_result[0]
    opp_odds = opp_result[0]

    # Playoff contender vs eliminated team
    if team_odds > 20 and opp_odds < 5:
        return config['points'], f"Playoff desperation: {team_odds:.0f}% vs {opp_odds:.0f}%"

    return 0.0, None


def check_revenge_game(cursor, team_abbr, opponent_abbr, season, week, weights):
    """
    Check for revenge game factor.

    Team facing opponent that beat them earlier this season: +1.0 points
    """
    config = weights['revenge_game']

    # Look for previous meeting
    cursor.execute("""
        SELECT g.home_score, g.away_score,
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
    """, [season, week, team_abbr, opponent_abbr, opponent_abbr, team_abbr])

    result = cursor.fetchone()
    if not result:
        return 0.0, None

    home_score, away_score, home_abbr, away_abbr = result

    # Determine if team lost previous meeting
    if home_abbr == team_abbr and home_score < away_score:
        return config['points'], f"Revenge game (lost previous meeting)"
    elif away_abbr == team_abbr and away_score < home_score:
        return config['points'], f"Revenge game (lost previous meeting)"

    return 0.0, None


def calculate_game_score(cursor, game, weights, thresholds, verbose=False):
    """Calculate situational score for a single game."""
    away_info = get_team_info(cursor, game['away_team_id'])
    home_info = get_team_info(cursor, game['home_team_id'])

    if not away_info or not home_info:
        return None

    season = game['season']
    week = game['week']

    # Calculate scores for each team
    away_factors = []
    home_factors = []

    # Bye week advantage (road team)
    score, reason = check_bye_week_advantage(
        cursor, away_info['abbr'], home_info['abbr'], season, week, True, weights
    )
    if score != 0:
        away_factors.append((score, reason, weights['bye_week_advantage']['confidence']))

    # Home after bye non-conference (home team)
    score, reason = check_home_after_bye_nonconf(
        cursor, home_info['abbr'], away_info['abbr'], season, week, True, weights
    )
    if score != 0:
        home_factors.append((score, reason, weights['home_after_bye_nonconference']['confidence']))

    # Extreme travel (away team)
    if game['travel_miles'] and game['timezone_change'] is not None:
        score, reason = check_extreme_travel(
            game['travel_miles'], game['timezone_change'], weights
        )
        if score != 0:
            away_factors.append((score, reason, weights['extreme_travel']['confidence']))

    # Morning body clock (away team)
    if game['travel_miles'] and game['timezone_change'] is not None:
        score, reason = check_morning_body_clock(
            cursor, away_info, home_info, game['game_time'], game['timezone_change'], weights
        )
        if score != 0:
            away_factors.append((score, reason, weights['morning_body_clock']['confidence']))

    # Primetime edge (away team)
    score, reason = check_primetime_edge(
        cursor, away_info['abbr'], home_info, game['game_time'], weights
    )
    if score != 0:
        away_factors.append((score, reason, weights['primetime_edge']['confidence']))

    # Short week (both teams)
    score, reason = check_short_week(cursor, game['game_date'], weights)
    if score != 0:
        # Apply to road team (disadvantage)
        away_factors.append((score, reason, weights['short_week_disadvantage']['confidence']))

    # Playoff desperation (both teams)
    score, reason = check_playoff_desperation(
        cursor, away_info['abbr'], home_info['abbr'], season, week, weights
    )
    if score != 0:
        away_factors.append((score, reason, weights['playoff_desperation']['confidence']))

    score, reason = check_playoff_desperation(
        cursor, home_info['abbr'], away_info['abbr'], season, week, weights
    )
    if score != 0:
        home_factors.append((score, reason, weights['playoff_desperation']['confidence']))

    # Revenge game (both teams)
    score, reason = check_revenge_game(
        cursor, away_info['abbr'], home_info['abbr'], season, week, weights
    )
    if score != 0:
        away_factors.append((score, reason, weights['revenge_game']['confidence']))

    score, reason = check_revenge_game(
        cursor, home_info['abbr'], away_info['abbr'], season, week, weights
    )
    if score != 0:
        home_factors.append((score, reason, weights['revenge_game']['confidence']))

    # Calculate total scores
    away_score = sum(f[0] for f in away_factors)
    home_score = sum(f[0] for f in home_factors)
    net_score = away_score - home_score  # Positive favors away, negative favors home

    return {
        'game_id': game['game_id'],
        'away_team': away_info['abbr'],
        'home_team': home_info['abbr'],
        'away_score': away_score,
        'home_score': home_score,
        'net_score': net_score,
        'away_factors': away_factors,
        'home_factors': home_factors,
        'favored_team': away_info['abbr'] if net_score > 0 else home_info['abbr'] if net_score < 0 else None,
        'edge_magnitude': abs(net_score),
        'travel_miles': game['travel_miles'],
        'timezone_change': game['timezone_change']
    }


def main():
    parser = argparse.ArgumentParser(description='Calculate situational scores for NFL games')
    parser.add_argument('--season', type=int, required=True, help='NFL season year')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--verbose', action='store_true', help='Show detailed factor breakdown')

    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    # Load configuration
    weights, thresholds = load_config()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get games for the week
    cursor.execute("""
        SELECT g.game_id, g.season, g.week, g.game_date, g.game_time,
               g.home_team_id, g.away_team_id, g.travel_miles, g.timezone_change
        FROM games g
        WHERE g.season = ? AND g.week = ?
        ORDER BY g.game_date, g.game_time
    """, [args.season, args.week])

    games = []
    for row in cursor.fetchall():
        games.append({
            'game_id': row[0],
            'season': row[1],
            'week': row[2],
            'game_date': row[3],
            'game_time': row[4],
            'home_team_id': row[5],
            'away_team_id': row[6],
            'travel_miles': row[7],
            'timezone_change': row[8]
        })

    if not games:
        print(f"❌ No games found for Week {args.week}, {args.season}")
        conn.close()
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"SITUATIONAL HANDICAPPING - Week {args.week}, {args.season}")
    print(f"{'='*70}\n")

    results = []
    for game in games:
        result = calculate_game_score(cursor, game, weights, thresholds, args.verbose)
        if result:
            results.append(result)

    # Sort by edge magnitude
    results.sort(key=lambda x: x['edge_magnitude'], reverse=True)

    # Display results
    override_threshold = thresholds['situational_score_thresholds']['override_threshold']
    strong_threshold = thresholds['situational_score_thresholds']['strong_tiebreaker_threshold']
    weak_threshold = thresholds['situational_score_thresholds']['weak_tiebreaker_threshold']

    print(f"Games with Situational Edges:\n")

    for result in results:
        if result['edge_magnitude'] >= weak_threshold:
            edge_type = ""
            if result['edge_magnitude'] >= override_threshold:
                edge_type = "HIGH CONFIDENCE"
            elif result['edge_magnitude'] >= strong_threshold:
                edge_type = "STRONG TIEBREAKER"
            else:
                edge_type = "WEAK TIEBREAKER"

            print(f"{result['away_team']} @ {result['home_team']}")
            print(f"  Edge: {result['favored_team']} {result['net_score']:+.1f} pts ({edge_type})")
            print(f"  Travel: {result['travel_miles']:.0f} miles, {result['timezone_change']:+d} TZ")

            if args.verbose:
                if result['away_factors']:
                    print(f"  {result['away_team']} factors:")
                    for score, reason, confidence in result['away_factors']:
                        print(f"    {score:+.1f} pts - {reason} (conf: {confidence}/10)")

                if result['home_factors']:
                    print(f"  {result['home_team']} factors:")
                    for score, reason, confidence in result['home_factors']:
                        print(f"    {score:+.1f} pts - {reason} (conf: {confidence}/10)")

            print()

    # Summary
    high_conf = len([r for r in results if r['edge_magnitude'] >= override_threshold])
    strong = len([r for r in results if strong_threshold <= r['edge_magnitude'] < override_threshold])
    weak = len([r for r in results if weak_threshold <= r['edge_magnitude'] < strong_threshold])

    print(f"Summary:")
    print(f"  High-confidence edges (≥{override_threshold} pts): {high_conf}")
    print(f"  Strong tiebreakers (≥{strong_threshold} pts): {strong}")
    print(f"  Weak tiebreakers (≥{weak_threshold} pts): {weak}")
    print(f"  Total games analyzed: {len(results)}")

    conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
