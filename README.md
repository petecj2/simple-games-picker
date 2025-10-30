# NFL Game Predictions for ESPN Pigskin Pick'em

A comprehensive NFL game prediction system using multiple analytical approaches to generate weekly picks for the ESPN Pigskin Pick'em contest.

## Overview

This project combines data-driven analysis from specialized agents with injury reports and betting market intelligence to predict NFL game outcomes. Each week's predictions are documented in a structured format that includes confidence levels, value plays, and upset alerts.

## Prediction Methodology

The system uses three main analytical approaches:

1. **ELO Power Ratings Analysis** - Statistical model based on team performance metrics
2. **Betting Market Analysis** - Sharp money indicators and line movement patterns
3. **Injury Impact Assessment** - Key player availability and game impact analysis

## Specialized Agents

### Neil Paine ELO Agent (`np-elo-agent`)

Uses Neil Paine's power rating methodology to predict games based on:
- **Data Source**: Neil Paine's Substack and GitHub repository
- **Methodology**: Simple Rating System with home field adjustments
- **Key Features**:
  - Power rating differentials between teams
  - Standard +2.5 point home field advantage
  - Win probability calculations using logistic regression
  - Confidence levels based on point differentials (High >7, Medium 3-7, Low <3)
- **Output**: Point spreads, win probabilities, and confidence ratings for each game

### Betting Line Agent (`betting-line-agent`)

Leverages betting market wisdom and sharp money indicators:
- **Data Sources**: Vegas Insider, Covers.com, OddsShark, Action Network
- **Methodology**: Market efficiency analysis and sharp vs. public money tracking
- **Key Features**:
  - Current betting lines and consensus spreads
  - Line movement analysis
  - Sharp money vs. public betting splits
  - Value opportunity identification
- **Output**: Market-based predictions, value plays, and contrarian opportunities

## Weekly Analysis Format

Each week's predictions are saved as `Week#.md` with the following structure:

### Synopsis Section
- **Game Winners**: Organized by day of the week
- **Confidence Levels**: High/Medium/Low confidence picks
- **Key Predictions**: High-confidence games, value plays, and upset alerts
- **Record Prediction**: Expected performance on high/medium confidence games

### Detailed Analysis
- **Neil Paine ELO Analysis**: Statistical predictions and confidence levels
- **Betting Market Analysis**: Sharp money indicators and line movements
- **Injury Report Analysis**: Impact of key player absences
- **Final Predictions**: Game-by-game picks with confidence ratings

## Usage

### Weekly Data Collection (Tuesday)

Before generating predictions, run these scripts to populate the database with current data:

1. **Process Neil Paine ELO Data**
   ```bash
   cd situational-handicapping/scripts/collection
   python3 process_nfl_html.py
   ```
   - Processes Neil Paine's weekly ELO ratings
   - Creates `weekX_predictions.md` with power ratings

2. **Scrape NFL Standings**
   ```bash
   python3 scrape_standings.py --season 2025 --week 9
   ```
   - Fetches current standings from ESPN API (automated)
   - Populates wins, losses, ties, division ranks, conference ranks
   - No manual download required

3. **Parse Playoff Odds**
   ```bash
   python3 parse_playoff_odds.py playoff_odds_week9.html --season 2025 --week 9 --format database
   ```
   - **Manual step**: Download HTML from [NFL.com Playoff Picture](https://www.nfl.com/playoffs/playoff-picture/)
   - Save as `playoff_odds_weekX.html` (week-numbered for historical tracking)
   - Extracts current playoff odds and win/loss scenario probabilities
   - Populates `if_win_playoff_odds` and `if_lose_playoff_odds` in database

### Generating Weekly Predictions

1. Run the prediction command for a specific week:
   ```
   Predict the game winners in Week [#] of the [year] NFL season
   ```

2. The system will:
   - Launch both specialized agents to gather their analyses
   - Compile injury reports from current sources
   - Generate a comprehensive `Week#.md` file
   - Clean up temporary files created by agents

3. Review the generated analysis and adjust picks as needed based on personal insights

## File Structure

```
simple-games-picking/
├── README.md                           # This file
├── CLAUDE.md                          # System instructions and format template
├── Week1.md                           # Week 1 predictions and analysis
├── Week2.md                           # Week 2 predictions (when generated)
└── .claude/
    └── agents/
        ├── np-elo-agent.md            # Neil Paine ELO prediction agent
        └── betting-line-agent.md      # Betting market analysis agent
```

## Key Features

- **Multi-source Analysis**: Combines statistical models with market intelligence
- **Confidence Ratings**: Clear differentiation between high, medium, and low confidence picks
- **Value Identification**: Highlights games where sharp money disagrees with public sentiment
- **Injury Impact**: Considers key player availability in predictions
- **Structured Output**: Consistent format for easy review and tracking

## Performance Tracking

Each week's file includes:
- Predicted record for high/medium confidence games
- Identified upset opportunities
- Value plays based on market inefficiencies

Results can be tracked against actual outcomes to refine the prediction methodology over time.

## Contributing

To improve the prediction system:
1. Update agent configurations in `.claude/agents/`
2. Refine the analysis template in `CLAUDE.md`
3. Add new data sources or analytical approaches
4. Track prediction accuracy to identify systematic improvements

## Notes

- Predictions are generated for the standard ESPN Pigskin Pick'em contest (picking winners only, not against the spread)
- The system prioritizes data-driven analysis while acknowledging the inherent uncertainty in NFL games
- Best used as one input among several when making final pick decisions

---

*This prediction system combines quantitative analysis with market intelligence to provide comprehensive NFL game predictions. Remember that no prediction system is perfect, and outcomes involve significant uncertainty.*