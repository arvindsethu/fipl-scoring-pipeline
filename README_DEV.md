
## Components

### 1. Match Data Scraping (`scorecard_scraper.py`)
- Scrapes live match data from ESPNCricinfo
- Extracts player statistics and data for batting, bowling and fielding
- Handles special cases like substitutes and player of the match
- Calculates performance differentials (strike rate, economy rate)

### 2. Score Calculation (`score_calculator.py`)
- Implements comprehensive scoring system based on player roles
- Calculates points for:
  - Batting (runs, strike rates, boundaries, milestones)
  - Bowling (wickets, economy, maidens, dot balls + more)
  - Fielding (catches, stumpings, run-outs)
  - Special awards (Player of the Match)
- Applies role-based multipliers and bonuses

### 3. Sheet Management (`sheet_updater.py`)
- Manages Google Sheets integration
- Updates player statistics and points
- Maintains gameweek and match-specific data
- Handles column mappings and data organization

### 4. Main Controller (`main.py`)
- Cloud Function entry point
- Manages match state and update cycles
- Coordinates between scraping, calculation, and update components

## Configuration Files

#### 1. Match Configuration (`ipl_2025_matches.json`)
```json
{
  "matches": [
    {
      "match_number": 1,
      "start_time": "2024-03-18T18:00:00Z",
      "status": "pending",
      "url": "espncricinfo-match-url",
      "gameweek": 1,
      "teams": {
        "Team1": {"gameweek_match": 1},
        "Team2": {"gameweek_match": 2}
      }
    }
  ]
}
```
- Maintains a static config of required real match data for all 2025 IPL matches

### 2. Scoring Rules (`scoring_rules.json`)
Defines point values for:
- Batting points
- Bowling points
- Fielding points
- Bonus points
- Role-based multipliers

### 3. Player Database (`players.json`)
Contains player information:
- Name
- Team
- Role (Batter, Bowler, Allrounder, Keeper)

### 4. Sheet Structure (`sheet_mappings.json`)
Defines Google Sheets layout:
- 15 gameweeks
- 2 matches per gameweek
- Column mappings for statistics
- Player name ranges

### 5. Field Mappings (`field_mappings.json`)
Maps scorecard fields to sheet columns for data consistency