# Fantasy IPL Scoring Pipeline

An automated scoring system for FIPL. This system automatically tracks live matches, calculates fantasy points, and updates scores in real-time to a Google Sheets.

## What it does

- **Live Match Tracking**: Automatically follows IPL matches as they happen
- **Real-time Scoring**: Updates player points every 15 minutes during matches
- **Scoring System**: 
  - Batting points for runs, strike rates, milestones and more
  - Bowling points for wickets, economy rates, and more
  - Fielding points for catches, run-outs, and stumpings
  - Special bonuses for Player of the Match

## How it works

The system runs automatically during match hours (9:30 AM to 8:00 PM UTC) and:
1. Tracks live match progress
2. Collects real-time player stats and data
3. Calculates points based on player performances
4. Updates scores to a Google Sheets dashboard
5. Can handle multiple matches simultaneously

## System Architecture

### Technologies Used

- **Google Cloud Platform**: For automation and execution
- **Google Sheets**: For displaying live scores and statistics
- **Python**: For data processing and calculations
- **ESPNCricinfo**: For live match data

### Cloud Infrastructure
- **Cloud Function**: Serverless function that processes match data and updates scores
- **Cloud Scheduler**: Triggers the function every 5 minutes during match hours
- **Google Sheets API**: Used for storing and displaying fantasy scores

### Update Frequency
The system uses dynamic update frequencies based on match progression:
- First 4 hours: Updates every 15 minutes
- Next hour: Updates every 30 minutes
- After 5 hours: Match marked as completed

## Development

For technical documentation, deployment commands, and testing instructions, see [README_DEV.md](README_DEV.md).

