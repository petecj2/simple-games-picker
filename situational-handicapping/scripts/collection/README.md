# Game Schedule Loading Scripts

## load_games_from_schedule.py

Generic script to load NFL game schedules into the database from multiple sources.

### Features

- **ESPN API Integration**: Automatically fetch schedules from ESPN (when available)
- **CSV Import**: Load schedules from manually-created CSV files
- **Markdown Parsing**: Parse schedules from existing prediction markdown files
- **Week-agnostic**: Works for any season and week combination

### Usage

#### Load from ESPN API (Preferred)

```bash
# Load a specific week
python load_games_from_schedule.py --season 2025 --week 11 --source espn

# Load entire season
python load_games_from_schedule.py --season 2025 --source espn

# Overwrite existing data without prompting
python load_games_from_schedule.py --season 2025 --week 11 --source espn --overwrite
```

#### Load from CSV File

Create a CSV file with the following format:

```csv
away_team,home_team,date,time,venue
GB,CHI,2025-11-13,13:00,Soldier Field
BUF,IND,2025-11-13,13:00,Lucas Oil Stadium
JAX,DET,2025-11-13,13:00,Ford Field
```

Then load it:

```bash
python load_games_from_schedule.py --season 2025 --week 11 --source csv --file data/schedule_week11.csv
```

#### Load from Markdown File

```bash
python load_games_from_schedule.py --season 2025 --week 10 --source markdown --file data/week10_predictions.md
```

### After Loading Games

Once games are loaded, you need to:

1. **Calculate travel distances** (requires team stadium data):
   ```bash
   python scripts/calculation/calculate_travel.py --season 2025 --week 11
   ```

2. **Generate situational analysis**:
   ```bash
   python scripts/calculation/generate_predictions.py --season 2025 --week 11 --output data/weekly_exports/
   ```

### Troubleshooting

**ESPN API Returns 500 Error**
- The ESPN API may be temporarily unavailable
- Future weeks may not have schedule data published yet
- Use CSV or markdown sources as alternatives

**"Team not found" Error**
- Ensure team abbreviations match those in the `teams` table
- Check `TEAM_NAME_TO_ABBR` mapping in the script for full name conversions

**CSV Format Issues**
- Ensure CSV has header row: `away_team,home_team,date,time,venue`
- Date format: `YYYY-MM-DD`
- Time format: `HH:MM` (24-hour)
- Team abbreviations must match database

### Replacement for Legacy Scripts

This script replaces the following week-specific scripts (now in `archive/historical_imports/`):
- `load_week8_from_predictions.py`
- `load_week9_games.py`
- `load_week10_games.py`
- `load_week9_from_predictions.py`

The deprecated `scrape_schedule.py` has been superseded by this unified approach.
