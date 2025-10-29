# NFL Situational Handicapping System

Research-backed situational handicapping system for NFL game prediction. Complements ELO and betting market analysis with context-aware situational factors including bye weeks, travel, motivation, and playoff implications.

## Overview

This system tracks and analyzes situational factors that traditional models underweight:
- **Bye Week Advantages:** Road favorites after bye (32-16 ATS, 66.7%, +14.4 units)
- **Morning Body Clock Games:** West Coast teams at 10am local time (64.4% home win rate)
- **Home After Bye (Non-Conference):** Fade home teams off bye vs non-conference opponents (26-13-2 ATS, 66.7%)
- **Travel & Time Zones:** Cross-country trips with multiple timezone changes
- **Primetime Performance:** Team-specific SNF/MNF/TNF records (33-22 ATS for West Coast teams)
- **Short Week Dynamics:** Thursday Night Football home/road splits

## Quick Start

### 1. Initialize Database

```bash
python scripts/database/init_database.py
```

Creates SQLite database with complete schema (teams, games, bye_weeks, standings, situational_trends, primetime_records).

### 2. Load Stadium Coordinates

Stadium coordinates for all 32 teams are already in `data/stadium_coordinates.json`.

### 3. Calculate Travel Distances

```bash
python scripts/calculation/calculate_travel.py --season 2025
```

Calculates haversine distance and timezone changes for all games.

## Project Structure

```
situational-handicapping/
├── data/
│   ├── nfl_games.db                    # SQLite database
│   ├── stadium_coordinates.json        # Team locations
│   └── weekly_exports/                 # Generated predictions
├── scripts/
│   ├── collection/                     # Data scraping scripts
│   ├── calculation/                    # Analysis scripts
│   │   └── calculate_travel.py         ✓ IMPLEMENTED
│   ├── database/                       # Database utilities
│   │   ├── init_database.py            ✓ IMPLEMENTED
│   │   └── query_helpers.py            ✓ IMPLEMENTED
│   └── utils/                          # Helper utilities
├── .claude/agents/                     # Claude Code subagent prompts
├── config/
│   ├── situational_weights.json        ✓ IMPLEMENTED
│   └── research_thresholds.json        ✓ IMPLEMENTED
└── README.md                           # This file
```

## Configuration

### situational_weights.json

All factors validated with research sources and URLs. Defines point adjustments:

**High-Confidence Factors (Confidence 7-8/10):**
- **Bye Week Advantage:** +3.0 points (VSiN: 32-16 ATS, 66.7%, +14.4 units, 48 games)
- **Morning Body Clock:** -3.0 points (Sports Insights: 64.4% home win rate, 374 games)
- **Home After Bye (Non-Conf):** -2.5 points (VSiN: 26-13-2 ATS, 66.7%, +11.7 units)

**Medium-Confidence Factors (Confidence 5-6/10):**
- **Primetime Edge:** +1.5 points (Sports Insights: 33-22 ATS, 60%)
- **Extreme Travel:** -2.0 points (>2000 miles + 3 TZ - trend reversed since 2013)
- **Short Week Disadvantage:** -1.0 points (TNF splits vary by week)

**Low-Confidence Factors (Confidence 3-4/10):**
- **Revenge Game:** +1.0 points (narrative-driven, limited research)
- **Playoff Desperation:** +2.0 points (Week 15+, general observation)
- **Lookahead Spot:** -1.5 points (trap game theory)
- **Division Game Home:** +0.5 points (familiarity advantage)

### research_thresholds.json

Defines thresholds for situational edge application:

- **Override Threshold:** ≥3.0 points (overrides ELO/Betting agreement)
- **Strong Tiebreaker:** ≥2.0 points (breaks ELO/Betting disagreements)
- **Weak Tiebreaker:** ≥1.0 points (minor influence)

## Database Schema

### teams
Team information with stadium coordinates, division, conference.

### games
Full season schedule with travel calculations, primetime flags, final scores.

### bye_weeks
Bye week schedule for each team with historical ATS performance.

### standings
Weekly standings with division rank, playoff odds, games behind.

### situational_trends
Research-backed situational trends with ATS records and confidence levels.

### primetime_records
Team-specific primetime performance (SNF, MNF, TNF) SU and ATS.

## Scripts Implemented

### ✓ init_database.py
Creates complete database schema with 6 tables and research-backed situational trends.

**Usage:**
```bash
python scripts/database/init_database.py
```

### ✓ calculate_travel.py
Calculates great circle distance using haversine formula and timezone changes.

**Usage:**
```bash
# All games for season
python scripts/calculation/calculate_travel.py --season 2025

# Specific week
python scripts/calculation/calculate_travel.py --season 2025 --week 9
```

### ✓ query_helpers.py
Database query utilities for accessing teams, games, standings, and situational data.

**Functions:**
- `get_team_by_abbreviation(abbr)`
- `get_games_for_week(season, week)`
- `get_team_bye_week(team_abbr, season)`
- `is_team_off_bye(team_abbr, season, week)`
- `get_current_standings(team_abbr, season, week)`
- `get_primetime_record(team_abbr, season, game_type)`
- `get_previous_matchup(team1_abbr, team2_abbr, season, before_week)`
- `get_situational_trend(situation_type)`

## Scripts To Be Implemented

### Data Collection
- [ ] `scrape_schedule.py` - ESPN API for full season schedule
- [ ] `scrape_standings.py` - Weekly ESPN standings with playoff odds
- [ ] `scrape_bye_weeks.py` - TeamRankings bye week ATS trends
- [ ] `track_revenge_games.py` - Identify rematches from previous meetings
- [ ] `scrape_primetime_records.py` - Pro Football Reference primetime performance

### Analysis
- [ ] `calculate_situational_score.py` - Apply weights to generate situational scores
- [ ] `generate_predictions.py` - Create weekly markdown predictions

### Utilities
- [ ] `update_game_results.py` - Record final scores and calculate ATS results
- [ ] `export_weekly_report.py` - Generate formatted weekly reports
- [ ] `validation.py` - Data quality checks

## Weekly Workflow

### Tuesday (Data Collection)
1. Scrape current standings
2. Update game results from previous week
3. Track revenge game opportunities

### Wednesday (Analysis)
1. Calculate situational scores for upcoming week
2. Research motivation factors
3. Identify high-confidence edges

### Friday (Integration)
1. Receive ELO and Betting agent picks
2. Apply situational adjustments
3. Generate final predictions

### Monday (Results & Learning)
1. Record game outcomes
2. Track situational factor performance
3. Adjust weights if needed

## Decision Tree

```
IF situational_score >= 4 AND backed by research (≥66% ATS):
    → OVERRIDE other agents (HIGH CONFIDENCE)

ELIF situational_score >= 3:
    → STRONG tiebreaker if ELO/Betting disagree

ELIF situational_score >= 2:
    → WEAK tiebreaker

ELSE:
    → Defer to ELO/Betting agents
```

## Research Sources

All situational factors validated with documented research:

- **VSiN (vsin.com):** Bye week situational trends with ATS records
  - Road favorites after bye vs divisional opponents: 32-16 ATS (66.7%)
  - Home teams after bye vs non-conference: 26-13-2 ATS (66.7% fade)
- **Sports Insights (sportsinsights.com):** Travel and primetime analysis
  - Morning body clock games: 64.4% home win rate (374 game sample)
  - West Coast teams in primetime traveling east: 33-22 ATS (60%)
- **TeamRankings (teamrankings.com):** Travel trends and ATS splits
  - Thursday Night Football home/road trends by week
  - West Coast to East Coast travel (trend reversal since 2013)
- **Pro Football Reference:** Historical game logs and primetime records
- **ESPN:** Standings, playoff probabilities (FPI)

## Performance Targets

- **High-confidence edges (≥4 pts):** 70%+ accuracy
- **Medium edges (2-3 pts):** 60-65% accuracy
- **Overall system:** 60-64% accuracy

## Dependencies

```bash
pip install sqlite3 pytz
```

## Implementation Status

**Phase 1: Foundation** ✓ COMPLETE
- [x] Database schema
- [x] Stadium coordinates
- [x] Travel calculations
- [x] Configuration files (validated with research sources)
- [x] Query helpers

**Phase 2: Data Collection** (In Progress)
- [ ] Schedule scraper
- [ ] Standings scraper
- [ ] Bye week scraper
- [ ] Primetime scraper
- [ ] Revenge game tracker

**Phase 3: Analysis** (Pending)
- [ ] Situational score calculator
- [ ] Prediction generator
- [ ] Weekly report exporter

**Phase 4: Integration** (Pending)
- [ ] Claude Code subagents
- [ ] Integration with ELO/Betting agents
- [ ] Performance tracking

## License

MIT

## Author

Part of the simple-games-picking NFL prediction system.
