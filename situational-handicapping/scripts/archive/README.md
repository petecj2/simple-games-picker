# Archive - Historical and Deprecated Scripts

This directory contains scripts that are no longer part of the active weekly workflow but are preserved for historical reference and potential future use.

## Directory Structure

### `setup/`
One-time setup scripts run during initial system configuration or at the start of each season.

- **`load_2025_bye_weeks.py`** - Loads 2025 bye week schedule into database
  - Run once per season
  - Could be replaced by automated scraping in future

### `historical_imports/`
Scripts used to import historical data for specific weeks. These were used during initial system setup and are preserved for reference.

- **`load_week8_from_predictions.py`** - Imported Week 8 game data from prediction files
- **`load_week9_from_predictions.py`** - Imported Week 9 game data from prediction files
- **`load_week9_games.py`** - Loaded Week 9 schedule into database
- **`update_week9_standings.py`** - Hardcoded Week 9 standings (superseded by `scrape_standings.py`)
  - Contains manually entered standings data
  - Now replaced by automated ESPN API scraping
- **`load_sample_standings.py`** - Sample data for testing/development

### `deprecated/`
Scripts that have been superseded by better implementations or are no longer needed.

- **`scrape_bye_weeks.py`** - Automated bye week scraping
  - Functionality exists but manual data entry preferred for accuracy
  - Could be reactivated if needed

- **`scrape_schedule.py`** - Automated schedule scraping
  - Functionality exists but manual data entry preferred for accuracy
  - Could be reactivated if needed

## Active Scripts (Not Archived)

For reference, the active weekly workflow uses these scripts:

**Collection (Weekly):**
- `collection/parse_playoff_odds.py` - Parse NFL.com playoff odds (manual HTML download)
- `collection/scrape_standings.py` - Fetch standings from ESPN API (automated)

**Calculation (Weekly):**
- `calculation/generate_predictions.py` - Generate situational analysis markdown
- `calculation/calculate_situational_score.py` - Core scoring logic
- `calculation/calculate_travel.py` - Travel distance and timezone calculations

**Database (Utilities):**
- `database/init_database.py` - Initialize database schema
- `database/load_teams.py` - Load NFL team reference data
- `database/verify_database.py` - Verify database integrity
- `database/query_helpers.py` - Common database query utilities

## Restoring Archived Scripts

If you need to restore any archived script:

```bash
# From situational-handicapping/scripts/ directory
git mv archive/[subdirectory]/[script.py] [target_directory]/
```

## Historical Context

These scripts were archived on 2025-10-30 as part of organizing the codebase after establishing the stable Tuesday weekly workflow:

1. Process Neil Paine ELO data (`process_nfl_html.py`)
2. Scrape standings from ESPN (`scrape_standings.py`)
3. Parse playoff odds from NFL.com (`parse_playoff_odds.py`)

The archived scripts served their purpose during system development and initial data loading, but are no longer part of the regular workflow.
