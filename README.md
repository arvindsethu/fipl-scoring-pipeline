# Fantasy IPL Scoring Pipeline

An automated scoring system for fantasy cricket, specifically designed for the Indian Premier League (IPL). This system automatically tracks live matches, calculates fantasy points, and updates scores in real-time to a Google Sheets dashboard.

## What it does

- **Live Match Tracking**: Automatically follows IPL matches as they happen
- **Real-time Scoring**: Updates player points every 15-30 minutes during matches
- **Comprehensive Scoring System**: 
  - Batting points for runs, strike rates, and milestones
  - Bowling points for wickets, economy rates, and dot balls
  - Fielding points for catches, run-outs, and stumpings
  - Special bonuses for Player of the Match

## How it works

The system runs automatically during match hours (9:30 AM to 8:00 PM UTC) and:
1. Tracks live match progress
2. Calculates points based on player performances
3. Updates scores to a Google Sheets dashboard
4. Handles multiple matches simultaneously

## Technologies Used

- **Google Cloud Platform**: For reliable automated execution
- **Google Sheets**: For displaying live scores and statistics
- **Python**: For data processing and calculations
- **ESPNCricinfo**: For live match data

## Scoring System Highlights

### Batting Points
- 1 point per run
- Bonus points for high strike rates
- Extra points for reaching milestones (30s, 50s, 100s)
- Boundary bonuses for fours and sixes

### Bowling Points
- Points for each wicket
- Economy rate bonuses
- Maiden over rewards
- Dot ball points

### Fielding Points
- Points for catches
- Points for stumpings
- Points for run-outs

### Special Awards
- Bonus points for Player of the Match

The system is designed to be fully automated, requiring no manual intervention during matches. All scores and statistics are automatically calculated and updated to provide a seamless fantasy cricket experience.

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
