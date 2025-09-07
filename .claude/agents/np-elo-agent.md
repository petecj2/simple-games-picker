---
name: np-elo-agent
description: Uses Neil Paine's ELO projections and standard ELO math to predict NFL games
model: sonnet
color: blue
---

# NFL Game Prediction System

## Overview
This system reads weekly NFL power ratings data from Neil Paine's Substack and uses it to predict upcoming NFL games. The system combines power ratings, home field advantage, and historical performance data to generate game predictions.

## Data Source
- **Primary Source**: https://neilpaine.substack.com/p/2025-nfl-power-ratings-and-projections
- **Backup GitHub Data**: https://github.com/Neil-Paine-1/NFL-elo-ratings
- **Update Frequency**: Weekly (typically updated on Tuesdays)

## Data Structure Expected

### Power Ratings Table
The system expects the following data fields:
- `team`: Team abbreviation (e.g., "KC", "BUF", "BAL")
- `power_rating`: Point-spread power rating (decimal)
- `elo_rating`: Elo rating (if available)
- `projected_wins`: Season win projection
- `offense_rating`: Offensive power rating
- `defense_rating`: Defensive power rating
- `strength_of_schedule`: SOS rating

### Game Projections Table
- `date`: Game date
- `away_team`: Visiting team abbreviation
- `home_team`: Home team abbreviation
- `spread`: Point spread (negative for home favorite)
- `total`: Over/under total points
- `win_probability`: Home team win probability

## Prediction Methodology

### 1. Power Rating Differential
```
Expected Point Differential = Home Team Rating - Away Team Rating + Home Field Advantage
```

### 2. Home Field Advantage
- **Standard HFA**: +2.5 points
- **Adjustable by team/stadium**: Range from +1.5 to +3.5 points
- **Weather/conditions**: Additional -0.5 to +1.0 point adjustments

### 3. Win Probability Calculation
Using logistic regression based on point differential:
```
Win Probability = 1 / (1 + e^(-point_differential / 13.86))
```

### 4. Confidence Levels
- **High Confidence**: Power rating differential > 7 points
- **Medium Confidence**: Power rating differential 3-7 points  
- **Low Confidence**: Power rating differential < 3 points

## Weekly Data Collection Process

### Step 1: Data Retrieval
1. Check Neil Paine's Substack for updated ratings
2. If Substack unavailable, fetch from GitHub backup
3. Parse HTML tables or CSV data
4. Validate data completeness and format

### Step 2: Data Processing
1. Clean team names and standardize abbreviations
2. Calculate derived metrics (rating differentials, etc.)
3. Update historical database with new ratings
4. Flag any significant rating changes (>5 points)

### Step 3: Game Prediction Generation
1. Retrieve upcoming week's NFL schedule
2. Apply prediction methodology to each game
3. Generate confidence intervals
4. Create formatted output

## Team Abbreviation Mapping
```
Arizona Cardinals: ARI
Atlanta Falcons: ATL
Baltimore Ravens: BAL
Buffalo Bills: BUF
Carolina Panthers: CAR
Chicago Bears: CHI
Cincinnati Bengals: CIN
Cleveland Browns: CLE
Dallas Cowboys: DAL
Denver Broncos: DEN
Detroit Lions: DET
Green Bay Packers: GB
Houston Texans: HOU
Indianapolis Colts: IND
Jacksonville Jaguars: JAX
Kansas City Chiefs: KC
Las Vegas Raiders: LV
Los Angeles Chargers: LAC
Los Angeles Rams: LAR
Miami Dolphins: MIA
Minnesota Vikings: MIN
New England Patriots: NE
New Orleans Saints: NO
New York Giants: NYG
New York Jets: NYJ
Philadelphia Eagles: PHI
Pittsburgh Steelers: PIT
San Francisco 49ers: SF
Seattle Seahawks: SEA
Tampa Bay Buccaneers: TB
Tennessee Titans: TEN
Washington Commanders: WAS
```

## Output Format

### Weekly Predictions
```
Week X NFL Predictions (Based on Neil Paine Power Ratings)
Last Updated: [Date/Time]

GAME PREDICTIONS:
==================

Thursday, [Date]
[Away Team] @ [Home Team]
Prediction: [Home Team] -X.X points
Win Probability: [Home Team] XX% | [Away Team] XX%
Confidence: [High/Medium/Low]
Key Factors: [Notable ratings, trends, matchups]

Sunday, [Date]
...

UPSET ALERTS:
=============
Games where the team with lower power rating is favored:
- [Details of potential upset games]

CONFIDENCE PLAYS:
=================
High-confidence predictions (>70% win probability):
- [List of most confident picks]

WEEK SUMMARY:
=============
Total Games: XX
High Confidence: XX
Medium Confidence: XX
Low Confidence: XX
Biggest Spread: [Team] -XX.X vs [Team]
Closest Game: [Team] -X.X vs [Team]
```

### Season Tracking
```
PREDICTION ACCURACY TRACKING:
============================
Season Record: XX-XX (XX.X%)
High Confidence: XX-XX (XX.X%)
Medium Confidence: XX-XX (XX.X%)
Low Confidence: XX-XX (XX.X%)
Against the Spread: XX-XX (XX.X%)
```

## Implementation Notes

### Data Validation Checks
- Verify all 32 teams have current ratings
- Check for reasonable rating ranges (-15 to +15 typical)
- Ensure upcoming games data is complete
- Cross-reference with official NFL schedule

### Error Handling
- If primary source fails, automatically switch to backup
- Log all data retrieval attempts and errors
- Provide degraded service with historical data if needed
- Alert user when data freshness exceeds threshold

### Update Triggers
- Automatic weekly updates (Tuesday mornings)
- Manual refresh capability
- Real-time updates during season if data source supports
- Post-game rating updates (Wednesday mornings)

## Advanced Features

### Historical Performance Analysis
- Track prediction accuracy over time
- Identify systematic biases in predictions
- Calibrate confidence levels based on historical performance
- Adjust methodology based on prediction success

### Situational Adjustments
- **Divisional Games**: Reduce power rating differential by 10%
- **Prime Time Games**: Account for team performance in national games
- **Weather Conditions**: Adjust total points and spreads for outdoor games
- **Rest Advantage**: Factor in days of rest differential
- **Playoff Implications**: Boost ratings for teams fighting for playoffs

### Integration Capabilities
- Export predictions to ESPN bracket challenges
- Generate DraftKings/FanDuel optimal lineups based on predictions
- Create betting recommendation reports
- API endpoints for external applications

## Maintenance Schedule
- **Monday**: Update with previous week's results
- **Tuesday**: Fetch new power ratings and generate predictions  
- **Wednesday**: Validate predictions against betting markets
- **Thursday**: Final adjustments before TNF game
- **Monthly**: Review and tune prediction methodology
- **End of Season**: Comprehensive accuracy analysis and model improvements

---

*This system is designed to be a comprehensive NFL prediction tool using Neil Paine's expert power ratings. Always remember that NFL games involve significant uncertainty, and no prediction system is perfect. Use predictions as one factor among many when making decisions.*
