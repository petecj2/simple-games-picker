-- Fix 2025 NFL Bye Week Schedule
-- Source: ESPN.com official 2025 bye week schedule
-- Date: 2025-10-30
--
-- This script corrects the bye_weeks table with the official 2025 NFL schedule.
-- 28 of 32 teams had incorrect bye weeks in the database.

BEGIN TRANSACTION;

-- Week 5 Byes: Atlanta, Chicago, Green Bay, Pittsburgh
UPDATE bye_weeks SET bye_week_number = 5
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('ATL', 'CHI', 'GB', 'PIT')
);

-- Week 6 Byes: Houston, Minnesota
UPDATE bye_weeks SET bye_week_number = 6
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('HOU', 'MIN')
);

-- Week 7 Byes: Baltimore, Buffalo
UPDATE bye_weeks SET bye_week_number = 7
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('BAL', 'BUF')
);

-- Week 8 Byes: Arizona, Detroit, Jacksonville, Las Vegas, LA Rams, Seattle
UPDATE bye_weeks SET bye_week_number = 8
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('ARI', 'DET', 'JAX', 'LV', 'LAR', 'SEA')
);

-- Week 9 Byes: Cleveland, NY Jets, Philadelphia, Tampa Bay
UPDATE bye_weeks SET bye_week_number = 9
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('CLE', 'NYJ', 'PHI', 'TB')
);

-- Week 10 Byes: Cincinnati, Dallas, Kansas City, Tennessee
UPDATE bye_weeks SET bye_week_number = 10
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('CIN', 'DAL', 'KC', 'TEN')
);

-- Week 11 Byes: Indianapolis, New Orleans
UPDATE bye_weeks SET bye_week_number = 11
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('IND', 'NO')
);

-- Week 12 Byes: Denver, LA Chargers, Miami, Washington
UPDATE bye_weeks SET bye_week_number = 12
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('DEN', 'LAC', 'MIA', 'WSH')
);

-- Week 14 Byes: Carolina, New England, NY Giants, San Francisco
UPDATE bye_weeks SET bye_week_number = 14
WHERE season = 2025 AND team_id IN (
    SELECT team_id FROM teams WHERE abbreviation IN ('CAR', 'NE', 'NYG', 'SF')
);

-- Update timestamp for all modified records
UPDATE bye_weeks
SET created_at = CURRENT_TIMESTAMP
WHERE season = 2025;

COMMIT;

-- Verification query - should return 32 teams with correct bye weeks
SELECT
    b.bye_week_number,
    GROUP_CONCAT(t.abbreviation, ', ') as teams,
    COUNT(*) as team_count
FROM bye_weeks b
JOIN teams t ON b.team_id = t.team_id
WHERE b.season = 2025
GROUP BY b.bye_week_number
ORDER BY b.bye_week_number;
