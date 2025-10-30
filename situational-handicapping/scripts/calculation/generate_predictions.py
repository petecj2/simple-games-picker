#!/usr/bin/env python3
"""
Generate weekly prediction markdown file based on situational analysis.

Creates formatted markdown output showing games with situational edges,
organized by confidence level with detailed reasoning.

Usage:
    python generate_predictions.py --season 2025 --week 9
    python generate_predictions.py --season 2025 --week 9 --output ../data/weekly_exports/
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

# Import scoring logic from calculate_situational_score
sys.path.append(str(SCRIPT_DIR))
from calculate_situational_score import (
    load_config, get_team_info, calculate_game_score
)


def format_date(date_str):
    """Format date string for display."""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%A, %B %d, %Y')
    except:
        return date_str


def get_factor_summary(factors):
    """Get short summary of factors for table."""
    if not factors:
        return "-"
    return "; ".join([f"{s:+.1f}" for s, r, c in factors])


def generate_markdown(season, week, results, thresholds):
    """Generate markdown content for predictions."""
    md = []

    md.append(f"# Week {week} Situational Handicapping Analysis\n")
    md.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    md.append("")

    # Synopsis Table
    md.append("## Synopsis - All Games\n")
    md.append("| Matchup | Travel | TZ | Playoff Odds | Bye Week | Body Clock | Extreme Travel | Primetime | Short Week | Desperation | Revenge | Total |")
    md.append("|---------|--------|----:|-------------:|---------:|-----------:|---------------:|----------:|-----------:|------------:|--------:|------:|")

    for result in results:
        matchup = f"{result['away_team']} @ {result['home_team']}"
        travel = f"{result['travel_miles']:.0f}mi"
        tz = f"{result['timezone_change']:+d}"

        # Extract individual factor scores
        bye_week = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'bye' in f[1].lower()])
        body_clock = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'body clock' in f[1].lower()])
        extreme_travel = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'Extreme travel' in f[1]])
        primetime = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'primetime' in f[1].lower()])
        short_week = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'Thursday' in f[1] or 'rest disadvantage' in f[1].lower()])
        revenge = get_factor_summary([f for f in result['away_factors'] + result['home_factors'] if 'revenge' in f[1].lower()])

        # Format playoff desperation (show both teams: away @ home)
        playoff = "-"
        away_desp = result.get('away_desperation')
        home_desp = result.get('home_desperation')

        if away_desp is not None and home_desp is not None:
            playoff = f"{away_desp:.0f}% @ {home_desp:.0f}%"
        elif away_desp is not None:
            playoff = f"{away_desp:.0f}% @ -"
        elif home_desp is not None:
            playoff = f"- @ {home_desp:.0f}%"

        # Calculate desperation score (only Week 9+)
        desperation = "-"
        if week >= 9 and away_desp is not None and home_desp is not None:
            # Calculate desperation differential
            desp_diff = abs(away_desp - home_desp)

            # Heuristic: Award points based on desperation gap
            # 10%+ gap = significant edge
            # 5-9% gap = moderate edge
            # <5% gap = minimal edge
            if desp_diff >= 10:
                desp_score = 2.0 if away_desp > home_desp else -2.0
                desperation = f"{desp_score:+.1f}"
            elif desp_diff >= 5:
                desp_score = 1.0 if away_desp > home_desp else -1.0
                desperation = f"{desp_score:+.1f}"

        total = f"{result['net_score']:+.1f}"

        md.append(f"| {matchup} | {travel} | {tz} | {playoff} | {bye_week} | {body_clock} | {extreme_travel} | {primetime} | {short_week} | {desperation} | {revenge} | **{total}** |")

    md.append("")

    # Legend
    md.append("**Column Legend:**")
    md.append("- **Travel**: Distance away team travels (miles)")
    md.append("- **TZ**: Timezone change (negative = traveling east, positive = traveling west)")
    md.append("- **Playoff Odds**: Playoff odds swing shown as away% @ home% (each team's playoff odds change between a win vs a loss)")
    md.append("- **Bye Week**: Road favorites after bye vs divisional opponents (+3.0 pts, 66.7% ATS)")
    md.append("- **Body Clock**: West Coast teams playing 10am local time on East Coast (-3.0 pts, 64.4% home win rate)")
    md.append("- **Extreme Travel**: >2000 miles + 3 TZ change (-2.0 pts)")
    md.append("- **Primetime**: West Coast teams in prime time traveling east (+1.5 pts, 60% ATS)")
    md.append("- **Short Week**: Rest disadvantage penalties (Thursday Night: -1.0, significant differential 2+ days: -0.5 per day, minor differential 1 day: -0.5)")
    md.append("- **Desperation**: Playoff desperation edge (Week 9+). ±2.0 pts for 10%+ gap, ±1.0 pts for 5-9% gap")
    md.append("- **Revenge**: Team facing opponent that beat them earlier (+1.0 pts)")
    md.append("- **Total**: Weighted sum of all factors (negative favors home, positive favors away)")
    md.append("")

    # Overview
    override_threshold = thresholds['situational_score_thresholds']['override_threshold']
    strong_threshold = thresholds['situational_score_thresholds']['strong_tiebreaker_threshold']
    weak_threshold = thresholds['situational_score_thresholds']['weak_tiebreaker_threshold']

    high_conf = [r for r in results if r['edge_magnitude'] >= override_threshold]
    strong = [r for r in results if strong_threshold <= r['edge_magnitude'] < override_threshold]
    weak = [r for r in results if weak_threshold <= r['edge_magnitude'] < strong_threshold]

    md.append("## Overview\n")
    md.append(f"Total games analyzed: **{len(results)}**\n")
    md.append(f"- High-confidence edges (≥{override_threshold} pts): **{len(high_conf)}**")
    md.append(f"- Strong tiebreakers ({strong_threshold}-{override_threshold-0.1} pts): **{len(strong)}**")
    md.append(f"- Weak tiebreakers ({weak_threshold}-{strong_threshold-0.1} pts): **{len(weak)}**")
    md.append(f"- No situational edge: **{len(results) - len(high_conf) - len(strong) - len(weak)}**\n")

    # High-confidence picks
    if high_conf:
        md.append("## 🔥 High-Confidence Picks (Override Other Models)\n")
        md.append(f"These games have situational edges ≥{override_threshold} points backed by research.\n")

        for result in high_conf:
            md.append(f"### {result['away_team']} @ {result['home_team']}\n")
            md.append(f"**Situational Pick: {result['favored_team']} ({result['net_score']:+.1f} pts)**\n")
            md.append(f"*Edge Type: HIGH CONFIDENCE OVERRIDE*\n")
            md.append(f"Travel: {result['travel_miles']:.0f} miles, {result['timezone_change']:+d} timezone change\n")

            md.append("**Situational Factors:**\n")

            if result['away_factors']:
                md.append(f"- **{result['away_team']}:**")
                for score, reason, confidence in result['away_factors']:
                    md.append(f"  - {score:+.1f} pts: {reason} (confidence: {confidence}/10)")

            if result['home_factors']:
                md.append(f"- **{result['home_team']}:**")
                for score, reason, confidence in result['home_factors']:
                    md.append(f"  - {score:+.1f} pts: {reason} (confidence: {confidence}/10)")

            md.append("")

    # Strong tiebreakers
    if strong:
        md.append("## 💪 Strong Tiebreakers\n")
        md.append(f"Use these to break ELO/Betting disagreements ({strong_threshold}-{override_threshold-0.1} pts).\n")

        for result in strong:
            md.append(f"### {result['away_team']} @ {result['home_team']}\n")
            md.append(f"**Situational Lean: {result['favored_team']} ({result['net_score']:+.1f} pts)**\n")
            md.append(f"Travel: {result['travel_miles']:.0f} miles, {result['timezone_change']:+d} TZ\n")

            md.append("**Factors:**\n")

            if result['away_factors']:
                md.append(f"- {result['away_team']}: " +
                         ", ".join([f"{s:+.1f} ({r[:30]}...)" for s, r, c in result['away_factors']]))

            if result['home_factors']:
                md.append(f"- {result['home_team']}: " +
                         ", ".join([f"{s:+.1f} ({r[:30]}...)" for s, r, c in result['home_factors']]))

            md.append("")

    # Weak tiebreakers
    if weak:
        md.append("## 📊 Weak Tiebreakers\n")
        md.append(f"Minor situational influences ({weak_threshold}-{strong_threshold-0.1} pts).\n")

        for result in weak:
            md.append(f"### {result['away_team']} @ {result['home_team']}\n")
            md.append(f"**Situational Lean: {result['favored_team']} ({result['net_score']:+.1f} pts)**\n")

            factor_summary = []
            if result['away_factors']:
                factor_summary.extend([r[:40] for s, r, c in result['away_factors']])
            if result['home_factors']:
                factor_summary.extend([r[:40] for s, r, c in result['home_factors']])

            if factor_summary:
                md.append(f"Factors: {', '.join(factor_summary)}\n")

    # Games with no edge
    no_edge = [r for r in results if r['edge_magnitude'] < weak_threshold]
    if no_edge:
        md.append("## 📋 No Significant Situational Edge\n")
        md.append("These games defer to ELO and betting market analysis.\n")

        for result in no_edge:
            md.append(f"- {result['away_team']} @ {result['home_team']}: "
                     f"{result['travel_miles']:.0f} miles, {result['timezone_change']:+d} TZ")

        md.append("")

    # Decision tree reminder
    md.append("---\n")
    md.append("## Decision Tree\n")
    md.append(f"- **≥{override_threshold} pts**: Override ELO/Betting (High Confidence)")
    md.append(f"- **≥{strong_threshold} pts**: Strong tiebreaker for disagreements")
    md.append(f"- **≥{weak_threshold} pts**: Weak tiebreaker")
    md.append("- **<1.0 pts**: Defer to ELO/Betting agents\n")

    # Methodology
    md.append("---\n")
    md.append("## Methodology\n")
    md.append("**High-Confidence Factors (7-8/10):**")
    md.append("- Bye Week Advantage: Road favorites after bye vs divisional (66.7% ATS)")
    md.append("- Morning Body Clock: West Coast teams at 10am local time (64.4% home win rate)")
    md.append("- Home After Bye (Non-Conf): Fade home teams off bye vs non-conference (66.7% ATS)\n")

    md.append("**Medium-Confidence Factors (5-6/10):**")
    md.append("- Extreme Travel: >2000 miles + 3 TZ change")
    md.append("- Primetime Edge: West Coast teams in prime time traveling east (60% ATS)")
    md.append("- Short Week: Thursday Night Football impacts\n")

    md.append("**Low-Confidence Factors (3-4/10):**")
    md.append("- Revenge games, playoff desperation, lookahead spots\n")

    md.append("All factors validated with research from VSiN, Sports Insights, and TeamRankings.")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description='Generate situational predictions markdown')
    parser.add_argument('--season', type=int, required=True, help='NFL season year')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--output', type=str, help='Output directory (optional)')

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

    # Calculate scores
    results = []
    for game in games:
        result = calculate_game_score(cursor, game, weights, thresholds, verbose=False)
        if result:
            results.append(result)

    # Sort by edge magnitude
    results.sort(key=lambda x: x['edge_magnitude'], reverse=True)

    # Generate markdown
    markdown_content = generate_markdown(args.season, args.week, results, thresholds)

    # Output
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"week{args.week}_situational.md"

        with open(output_file, 'w') as f:
            f.write(markdown_content)

        print(f"✅ Predictions written to: {output_file}")
    else:
        print(markdown_content)

    conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
