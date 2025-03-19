# Fantasy IPL Scoring Pipeline

A cloud-based automated scoring system for fantasy cricket, specifically designed for the Indian Premier League (IPL). The system scrapes live match data, calculates fantasy points based on player performances, and updates scores in real-time to a Google Sheets dashboard.

## System Architecture

### Cloud Infrastructure
- **Cloud Function**: Serverless function that processes match data and updates scores
- **Cloud Scheduler**: Triggers the function every 5 minutes between 8 AM and 8 PM UTC
- **Google Sheets API**: Used for storing and displaying fantasy scores

### Update Frequency
The system uses dynamic update frequencies based on match progression:
- First 4 hours: Updates every 15 minutes
- Next hour: Updates every 30 minutes
- After 5 hours: Match marked as completed

## Components

### 1. Match Data Scraping (`scorecard_scraper.py`)
- Scrapes live match data from ESPNCricinfo
- Extracts detailed statistics for batting, bowling, and fielding
- Handles special cases like substitutes and player of the match
- Calculates performance differentials (strike rate, economy rate)

### 2. Score Calculation (`score_calculator.py`)
- Implements comprehensive scoring system based on player roles
- Calculates points for:
  - Batting (runs, strike rates, boundaries, milestones)
  - Bowling (wickets, economy, maidens, dot balls)
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
- Implements error handling and logging

## Configuration Files

### 1. Match Configuration (`demo.json`)
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

### 2. Scoring Rules (`scoring_rules.json`)
Defines point values for:
- Run scoring (runs, boundaries, milestones)
- Strike rate bonuses/penalties
- Economy rate bonuses/penalties
- Wicket bonuses
- Fielding points
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

## Tournament Structure
- 15 gameweeks total
- Maximum 2 matches per team per gameweek
- Scores tracked and updated throughout the tournament
- Running totals maintained for each gameweek

## Setup Requirements

### Google Cloud
1. Enable required APIs:
   - Cloud Functions
   - Cloud Scheduler
   - Google Sheets API

### Service Account
1. Create a service account with necessary permissions
2. Download credentials and save as `service-account.json`
3. Share target Google Sheet with service account email

### Python Dependencies
```
google-cloud-functions-framework
google-oauth2-tool
google-api-python-client
beautifulsoup4
requests
pytz
```

## Usage

### Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up service account credentials
4. Run locally: `python main.py`

### Deployment
1. Deploy to Google Cloud Functions
2. Set up Cloud Scheduler trigger
3. Configure environment variables:
   - Timezone settings
   - Sheet ID
   - Service account path

## Monitoring
- Cloud Function logs available in Google Cloud Console
- Error handling and logging implemented
- Match state tracking in `demo.json`

## Limitations
- ESPNCricinfo rate limiting considerations
- Google Sheets API quotas
- Cloud Function timeout limits

## Contributing
[Add contribution guidelines if applicable]

## License
[Add license information]
