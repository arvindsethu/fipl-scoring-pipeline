# Development Guide

## Quick Reference Commands

### Deployment Commands

#### Deploy Cloud Function
```bash
gcloud functions deploy fipl-score-updater --gen2 --runtime=python39 --region=europe-west2 --source=. --entry-point=update_scores --trigger-http --memory=1024MB --timeout=540s --min-instances=0 --max-instances=1 --service-account=fipl-scoring-service@intense-context-454213-u3.iam.gserviceaccount.com --allow-unauthenticated
```

#### Update Match Configuration in Cloud Storage
```bash
# Download current state from bucket
gsutil cp gs://fipl_bucket/match_states/ipl_2025_matches.json config/ipl_2025_matches.json 

# Upload updated configuration to bucket
gsutil cp config/ipl_2025_matches.json gs://fipl_bucket/match_states/ipl_2025_matches.json
```

### Manual Testing Commands

#### Process Specific Match (Full Pipeline)
```bash
python manual_tools/scripts/run_pipeline.py --match-number <number>
```

#### Process Match in Dry Run Mode (No Sheet Updates)
```bash
python manual_tools/scripts/run_pipeline.py --match-number <number> --dry
```

#### Process Any Scorecard URL (Scraping Only)
```bash
python manual_tools/scripts/run_pipeline.py --url <scorecard_url>
```

#### Examples
```bash
# Process match 5 with full sheet updates
python manual_tools/scripts/run_pipeline.py --match-number 5

# Test match 5 without affecting live data
python manual_tools/scripts/run_pipeline.py --match-number 5 --dry

# Process any ESPNCricinfo scorecard
python manual_tools/scripts/run_pipeline.py --url "https://www.espncricinfo.com/series/..."
```

---

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

### 5. Manual Testing Tools (`manual_tools/`)
- Local testing and demonstration utilities
- Output is always saved to `manual_tools/outputs/scorecard.json`
- Handles quoted and unquoted URLs
- Provides progress feedback during execution

#### Three modes of operation:

1. **Match Number Mode**: Reads match data from `ipl_2025_matches.json`, runs complete pipeline including sheet updates
2. **Direct URL Mode**: Processes any ESPNCricinfo scorecard URL, runs scraper and calculator only (no sheet updates)  
3. **Dry Run Mode**: Uses match data from `ipl_2025_matches.json`, runs complete pipeline but skips sheet updates

See command reference at the top of this document for usage examples.

## Configuration Files

#### 1. Match Configuration (`ipl_2025_matches.json`)
```json
{
  "matches": [
    {
      "match_number": 1,
      "start_time": "2024-03-18T18:00:00Z",
      "status": "not_started",
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